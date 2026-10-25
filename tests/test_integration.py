"""Integration regressions for provider routing, reconnect ownership and Qt state."""
import asyncio
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,MagicMock,patch
import threading

import main
from core import storage
from core.execution import BoundedExecutor
from core.speech_output import SpeechOutput
from google.genai import types


def fixture():
    live=main.JarvisLive.__new__(main.JarvisLive)
    live.ui=SimpleNamespace(muted=False,write_log=MagicMock(),set_state=MagicMock(),
        clear_jarvis_response=MagicMock(),stream_jarvis_chunk=MagicMock(),
        _win=SimpleNamespace(_shutdown_sig=MagicMock(),_holo_sig=MagicMock()),
        on_wake=None,on_speak=None,on_shutdown=None)
    live.session=None;live.is_sleeping=True;live.last_speech_time=0
    live.noise_gate_threshold=.003;live.sleep_after=20;live._provider="gemini"
    live._is_speaking=False;live._is_busy=False;live._speaking_lock=threading.Lock()
    live._stop_requested=threading.Event();live._speech_output=SpeechOutput()
    live._tool_tasks=set();live._resume_handle=None;live._local_speech_active=False
    live._response_started=None;live.audio_drops=0;live.audio_status="";live._capture=None
    live._turn_done_event=None;live._api_1011_tool=None;live.vosk_recognizer=None
    live._loop=asyncio.get_running_loop()
    live._speech_queue=asyncio.Queue(maxsize=8);live._text_queue=asyncio.Queue(maxsize=8)
    live.out_queue=asyncio.Queue(maxsize=32);live.audio_in_queue=asyncio.Queue(maxsize=120)
    live._tool_lock=asyncio.Lock();live._reconnect_event=asyncio.Event()
    live._audio_restart=asyncio.Event()
    live._fire_phrase_triggers=lambda text:False
    return live


class RuntimeIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_typed_local_command_works_without_cloud(self):
        live=fixture()
        live._execute_tool=AsyncMock(return_value=types.FunctionResponse(name="get_current_time",response={"result":"Son las 10"}))
        await live._dispatch_text("qué hora es")
        live._execute_tool.assert_awaited_once()
        self.assertFalse(live.is_sleeping)
        self.assertGreater(live.last_speech_time,0)
        self.assertTrue(any("Son las 10" in str(call) for call in live.ui.write_log.call_args_list))

    async def test_audio_from_disconnected_session_is_not_queued(self):
        live=fixture();live.is_sleeping=False
        live.send_audio(b"test")
        await asyncio.sleep(0)
        self.assertEqual(live.out_queue.qsize(),0)

    async def test_queued_audio_cannot_cross_reconnect(self):
        live=fixture();live.is_sleeping=False;live.session=object()
        live.send_audio(b"test")
        live.session=object()
        await asyncio.sleep(0)
        self.assertEqual(live.out_queue.qsize(),0)

    async def test_tool_response_never_sent_to_new_session(self):
        live=fixture()
        old=SimpleNamespace(send_tool_response=AsyncMock())
        new=SimpleNamespace(send_tool_response=AsyncMock())
        live.session=old
        async def execute(fc):
            live.session=new
            return types.FunctionResponse(id=fc.id,name=fc.name,response={"result":"done"})
        live._execute_tool=execute
        await live._handle_tool_calls([SimpleNamespace(name="x",id="1")],old)
        old.send_tool_response.assert_not_awaited()
        new.send_tool_response.assert_not_awaited()

    async def test_ollama_tool_round_trip(self):
        live=fixture();live._provider="ollama"
        cfg={"ai_provider":"ollama","ollama_model":"test"}
        replies=[
            {"role":"assistant","content":"","tool_calls":[{"function":{"name":"get_current_time","arguments":{}}}]},
            {"role":"assistant","content":"Son las 10."}]
        provider=MagicMock()
        def chat(messages,tools):
            result=replies.pop(0)
            if not replies:
                self.assertEqual(messages[-1]["role"],"tool")
                self.assertEqual(messages[-1]["tool_name"],"get_current_time")
                live._loop.call_soon_threadsafe(live._loop.call_later,0.05,live._reconnect_event.set)
            return result
        provider.chat.side_effect=chat
        live._execute_tool=AsyncMock(return_value=types.FunctionResponse(name="get_current_time",response={"result":"10:00","ok":True}))
        live._text_queue.put_nowait("dime la hora por favor")
        with patch("memory.config_manager.load_api_keys",return_value=cfg),patch("core.text_provider.TextProvider",return_value=provider),patch.object(main,"_load_system_prompt",return_value="Kler"):
            await asyncio.wait_for(live._run_text_provider(),timeout=2)
        live._execute_tool.assert_awaited_once()
        live.ui.stream_jarvis_chunk.assert_called_once_with("Son las 10.")

    async def test_provider_change_ignores_inflight_old_response(self):
        live=fixture()
        gate=threading.Event()
        started=threading.Event()
        def chat(*args):
            started.set()
            gate.wait(2)
            return {"role":"assistant","content":"old"}
        provider=SimpleNamespace(chat=chat)
        pool=BoundedExecutor(max_workers=1,max_pending=1)
        try:
            with patch.object(main,"_HTTP_EXECUTOR",pool):
                task=asyncio.create_task(live._request_text(provider,[],[]))
                for _ in range(50):
                    if started.is_set():
                        break
                    await asyncio.sleep(0.01)
                live._reconnect_event.set()
                self.assertIsNone(await asyncio.wait_for(task,timeout=0.5))
        finally:
            gate.set()
            pool.shutdown(wait=True)

    async def test_disabled_tool_is_not_executed(self):
        live=fixture()
        live._execute_tool_impl=AsyncMock()
        with patch("memory.config_manager.load_api_keys",return_value={"enabled_tools":[]}):
            result=await live._execute_tool(SimpleNamespace(name="auto_programmer",id="1",args={}))
        self.assertIn("error",result.response)
        live._execute_tool_impl.assert_not_awaited()

    async def test_failure_result_is_structured(self):
        live=fixture()
        live._execute_tool_impl=AsyncMock(return_value=types.FunctionResponse(name="open_app",response={"result":"Error: no existe"}))
        with patch("memory.config_manager.load_api_keys",return_value={}):
            result=await live._execute_tool(SimpleNamespace(name="open_app",id="1",args={}))
        self.assertFalse(result.response["ok"])
        self.assertIn("no existe",result.response["error"])

    async def test_capture_starts_while_gemini_has_no_key(self):
        live=fixture()
        capture_started=asyncio.Event()
        async def listen():
            capture_started.set()
            await asyncio.Future()
        async def pending():
            await asyncio.Future()
        live._listen_audio=listen;live._speech_loop=pending;live._optional_services=pending
        with patch("memory.config_manager.load_api_keys",return_value={"ai_provider":"gemini"}),patch.object(main,"_get_api_key",return_value=""),patch("core.jobs.start_runner"),patch("core.jobs.stop_runner"),patch.object(main,"start_rules_runner"),patch("core.preflight.inspect_installation",return_value=[]),patch.object(main,"_TOOL_EXECUTOR",BoundedExecutor(max_workers=1)),patch.object(main,"_HTTP_EXECUTOR",BoundedExecutor(max_workers=1)):
            task=asyncio.create_task(live.run())
            await asyncio.wait_for(capture_started.wait(),timeout=2)
            self.assertIsNone(live.session)
            live._shutdown_event.set()
            await asyncio.wait_for(task,timeout=2)

    async def test_live_schema_matches_installed_sdk(self):
        live=fixture()
        with patch.object(main,"load_memory",return_value={}),patch.object(main,"_load_system_prompt",return_value="Kler"),patch.object(main,"_load_tz"),patch("memory.config_manager.load_api_keys",return_value={}):
            config=live._build_config()
        self.assertLess(len(config.tools[0].function_declarations),30)
        self.assertIsNotNone(config.session_resumption)


class QtIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ui
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        import ui
        from PyQt6.QtWidgets import QWidget
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        state=patch.object(storage,"DB_PATH",Path(self.temp.name)/"ui.sqlite3")
        state.start();self.addCleanup(state.stop)
        def orb_init(orb,owner,parent=None):
            QWidget.__init__(orb,parent)
            orb.ui=owner;orb.web_view=None
        for patcher in [patch.object(ui.CustomParticleOrb,"__init__",orb_init),
                        patch.object(ui.JarvisUI,"ensure_startup_shortcut",lambda s:None),
                        patch.object(ui.MainWindow,"_setup_tray_icon",lambda s:None)]:
            patcher.start();self.addCleanup(patcher.stop)
        self.window=ui.JarvisUI()
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window._win.notes_w._save_timer.stop()
        self.window._win._force_close=True
        self.window._win.close()
        self.app.processEvents()

    def test_state_changes_do_not_remove_manual_mute(self):
        for state in ["SPEAKING","LISTENING","THINKING","SLEEPING"]:
            self.window.muted=True
            self.window.set_state(state)
            self.assertTrue(self.window.muted)

    def test_history_displays_errors(self):
        self.window.write_log("Error: prueba de diagnóstico")
        self.app.processEvents()
        self.assertIn("prueba de diagnóstico",self.window._win.history_log.toPlainText())

    def test_wake_button_reaches_engine(self):
        self.window.on_wake=MagicMock()
        self.window.muted=True
        self.window._win._wake_sig.emit()
        self.app.processEvents()
        self.window.on_wake.assert_called_once()
        self.assertFalse(self.window.muted)

    def test_notes_and_todos_persist(self):
        from PyQt6.QtTest import QTest
        self.window._win.notes_w.txt_notes.setPlainText("Guardar esta nota")
        QTest.qWait(350)
        self.window._win.todo_w.txt_task.setText("Tarea persistente")
        self.window._win.todo_w.add_task()
        self.assertEqual(storage.get_state("notes"),"Guardar esta nota")
        self.assertEqual(storage.get_state("todos")[0]["text"],"Tarea persistente")
