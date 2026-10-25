"""Regression tests without microphone capture, account access or desktop automation."""
import ast
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from core import storage,jobs
from core.voice_input import VoiceInput,WAKE_RE,device_id
from core.text_provider import TextProvider,json_schema
from core.execution import BoundedExecutor


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"test.sqlite3"
        patcher=patch.object(storage,"DB_PATH",self.path)
        patcher.start();self.addCleanup(patcher.stop)

    def test_state_survives_another_process(self):
        storage.set_state("notes","Persistente: acción Ñ")
        env=dict(os.environ,KLER_DB_PATH=str(self.path),PYTHONUTF8="1")
        result=subprocess.run([sys.executable,"-c","from core.storage import get_state; print(get_state('notes'))"],
                              cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("acción Ñ",result.stdout)

    def test_transaction_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with storage.connection() as db:
                db.execute("INSERT INTO state VALUES('test','1')")
                raise RuntimeError()
        self.assertIsNone(storage.get_state("test"))

    def test_reminder_absolute_date_is_not_one_minute(self):
        from actions.reminder import reminder
        due=datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        due+=timedelta(days=2)
        with patch("actions.reminder.start_runner"):
            result=reminder({"date":due.strftime("%Y-%m-%d"),"time":"15:30","message":"Médico"})
        self.assertNotIn("Error",result)
        saved=jobs.list_jobs()[0]
        self.assertEqual(datetime.fromtimestamp(saved["due"],jobs.local_now().tzinfo).hour,15)
        self.assertEqual(saved["action"],"notify")

    def test_bad_reminder_not_saved(self):
        from actions.reminder import reminder
        self.assertIn("Error",reminder({"time":"mañana","message":"hola"}))
        self.assertEqual(jobs.list_jobs(),[])

    def test_reminder_uses_supported_voice_callback(self):
        speaker=MagicMock()
        player=SimpleNamespace(write_log=MagicMock())
        result=jobs.execute_action("notify",{"message":"Tomar agua"},player,speaker)
        speaker.assert_called_once_with("Tomar agua")
        self.assertEqual(result,"Tomar agua")

    def test_due_job_runs_once_even_if_tick_repeated(self):
        jobs.create_job("agua",time.time()-1,"notify",{"message":"agua"})
        speaker=MagicMock()
        runner=jobs.JobRunner(speak=speaker)
        runner.tick();runner.tick()
        runner.pool.shutdown(wait=True)
        speaker.assert_called_once_with("agua")
        self.assertEqual(jobs.list_jobs()[0]["status"],"done")

    def test_failed_job_records_error(self):
        jobs.create_job("bad",time.time()-1,"backup",{"source":str(Path(self.temp.name)/"missing"),"destination":str(Path(self.temp.name)/"copy")})
        runner=jobs.JobRunner()
        runner.tick();runner.pool.shutdown(wait=True)
        job=jobs.list_jobs()[0]
        self.assertEqual(job["status"],"failed")
        self.assertTrue(job["last_error"])

    def test_recurring_job_advances_without_replaying_all_missed_intervals(self):
        jobs.create_job("repeat",time.time()-500,"notify",{"message":"hola"},"interval",60)
        runner=jobs.JobRunner()
        runner.tick();runner.pool.shutdown(wait=True)
        job=jobs.list_jobs()[0]
        self.assertEqual(job["status"],"pending")
        self.assertGreater(job["due"],time.time())

    def test_disable_and_delete_jobs(self):
        identity=jobs.create_job("x",time.time()+10,"notify",{})
        jobs.change_job(identity[:6],"disable")
        self.assertEqual(jobs.list_jobs()[0]["enabled"],0)
        jobs.change_job(identity,"delete")
        self.assertEqual(jobs.list_jobs(),[])

    def test_running_job_not_repeated_on_restart(self):
        identity=jobs.create_job("external",time.time()-10,"notify",{})
        with storage.connection() as db:
            db.execute("UPDATE jobs SET status='running' WHERE id=?",(identity,))
        runner=jobs.JobRunner()
        runner.start();runner.stop()
        self.assertEqual(jobs.list_jobs()[0]["status"],"failed")

    def test_rules_persist_and_execute_real_notify(self):
        from actions import rules_engine as rules
        player=SimpleNamespace(write_log=MagicMock())
        speaker=MagicMock()
        rules.start_rules_runner(player,speaker)
        result=rules.rules_engine({"action":"create","name":"agua","phrase":"tengo sed","task_action":{"type":"notify","parameters":{"message":"Bebe agua"}}})
        self.assertNotIn("Error",result)
        matching=rules.check_phrase_triggers("Kler tengo sed")
        self.assertEqual(len(matching),1)
        rules._run_action(matching[0]["action"]).result(timeout=3)
        speaker.assert_called_once_with("Bebe agua")
        rules.rules_engine({"action":"disable","name":"agua"})
        self.assertEqual(rules.check_phrase_triggers("tengo sed"),[])

    def test_knowledge_is_saved_and_searchable(self):
        from actions.knowledge_base import knowledge_base
        knowledge_base({"action":"add","title":"Diseño","content":"Tema cian","tags":"interfaz"})
        result=json.loads(knowledge_base({"action":"search","query":"cian"}))
        self.assertEqual(result[0]["title"],"Diseño")

    def test_preferences_are_updated(self):
        from actions.user_profile import user_profile
        user_profile({"action":"set_name","name":"David"})
        self.assertEqual(json.loads(user_profile({"action":"view"}))["name"],"David")


class FakeRecognizer:
    def __init__(self,steps):
        self.steps=iter(steps);self.current={};self.calls=0
    def AcceptWaveform(self,data):
        self.calls+=1;self.current=next(self.steps,{"final":False,"partial":""})
        return self.current.get("final",False)
    def Result(self):return json.dumps({"text":self.current.get("text","")})
    def PartialResult(self):return json.dumps({"partial":self.current.get("partial","")})
    def Reset(self):pass


class FakeOwner:
    def __init__(self):
        self.ui=SimpleNamespace(muted=False,set_audio_level=MagicMock())
        self.is_sleeping=True;self._is_speaking=False;self._is_busy=False
        self.noise_gate_threshold=.003;self.last_speech_time=0;self.sleep_after=20
        self.audio=[];self.commands=[]
    def wake(self):self.is_sleeping=False
    def sleep(self):self.is_sleeping=True
    def send_audio(self,data):self.audio.append(data)
    def voice_text(self,text):self.commands.append(text)


class VoiceTests(unittest.TestCase):
    def test_name_is_not_matched_inside_another_word(self):
        self.assertIsNone(WAKE_RE.search("esclerótico"))
        self.assertIsNotNone(WAKE_RE.search("oye Kler abre Spotify"))
        self.assertIsNone(WAKE_RE.search("Jarvis"))

    def test_same_utterance_keeps_command_and_preroll(self):
        owner=FakeOwner()
        recognizer=FakeRecognizer([{"partial":"oye"},{"partial":"kler"},{"final":True,"text":"kler abre spotify"}])
        engine=VoiceInput(owner,recognizer)
        data=b"\x00\x02"*512
        engine.process(data,now=1)
        self.assertEqual(owner.audio,[])
        engine.process(data,now=1.2)
        engine.process(data,now=1.4)
        self.assertFalse(owner.is_sleeping)
        self.assertEqual(owner.commands,["abre spotify"])
        self.assertEqual(len(owner.audio),3)

    def test_manual_mute_prevents_wake_and_audio(self):
        owner=FakeOwner();owner.ui.muted=True
        recognizer=FakeRecognizer([{"partial":"kler"}])
        engine=VoiceInput(owner,recognizer)
        engine.process(b"\x00\x00"*512,now=2)
        self.assertTrue(owner.is_sleeping);self.assertEqual(recognizer.calls,0)
        self.assertEqual(owner.audio,[])

    def test_silence_is_forwarded_to_finish_server_vad(self):
        owner=FakeOwner();owner.is_sleeping=False;owner.last_speech_time=1
        engine=VoiceInput(owner)
        data=b"\x00\x00"*512
        engine.process(data,now=1.5)
        self.assertEqual(owner.audio,[data])

    def test_idle_returns_to_sleep_without_muting(self):
        owner=FakeOwner();owner.is_sleeping=False;owner.last_speech_time=1
        VoiceInput(owner).process(b"\x00\x00"*512,now=25)
        self.assertTrue(owner.is_sleeping);self.assertFalse(owner.ui.muted)

    def test_callback_never_runs_recognition_and_is_bounded(self):
        owner=FakeOwner();recognizer=FakeRecognizer([])
        engine=VoiceInput(owner,recognizer)
        for _ in range(100):
            engine.callback(b"\x00\x00"*512,512,None,None)
        self.assertEqual(recognizer.calls,0);self.assertEqual(engine.queue.qsize(),32)
        self.assertEqual(engine.dropped,68)

    def test_selected_input_device_is_used(self):
        import sounddevice
        engine=VoiceInput(FakeOwner())
        with patch.object(sounddevice,"check_input_settings") as check,patch.object(sounddevice,"RawInputStream") as stream:
            engine.start("3");engine.close()
        self.assertEqual(stream.call_args.kwargs["device"],3)
        self.assertEqual(check.call_args.kwargs["device"],3)


class ProviderTests(unittest.TestCase):
    def test_nested_schema_types_are_converted(self):
        result=json_schema({"type":"OBJECT","properties":{"x":{"type":"ARRAY","items":{"type":"STRING"}}}})
        self.assertEqual(result["properties"]["x"]["items"]["type"],"string")

    def test_ollama_receives_tools_and_returns_real_tool_call(self):
        response=MagicMock(status_code=200)
        message={"role":"assistant","tool_calls":[{"function":{"name":"get_current_time","arguments":{}}}]}
        response.json.return_value={"message":message}
        provider=TextProvider({"ai_provider":"ollama","ollama_model":"test"})
        with patch("requests.post",return_value=response) as post:
            self.assertEqual(provider.chat([{"role":"user","content":"hora"}],[{"name":"get_current_time","description":"time","parameters":{"type":"OBJECT","properties":{}}}]),message)
        self.assertIn("/api/chat",post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["json"]["tools"][0]["function"]["parameters"]["type"],"object")

    def test_ollama_model_without_tools_can_still_chat(self):
        rejected=MagicMock(status_code=400,text="model does not support tools")
        accepted=MagicMock(status_code=200)
        accepted.json.return_value={"message":{"role":"assistant","content":"Hola"}}
        provider=TextProvider({"ai_provider":"ollama"})
        with patch("requests.post",side_effect=[rejected,accepted]) as post:
            result=provider.chat([{"role":"user","content":"hola"}],[{"name":"x","description":"x"}])
        self.assertEqual(result["content"],"Hola")
        self.assertFalse(provider.supports_tools)
        self.assertEqual(post.call_count,2)

    def test_openrouter_missing_key_is_reported_before_http(self):
        with patch("requests.post") as post,self.assertRaises(ValueError):
            TextProvider({"ai_provider":"openrouter"}).chat([],[])
        post.assert_not_called()

    def test_quota_error_is_not_immediately_retried(self):
        with patch("requests.post",return_value=MagicMock(status_code=429)) as post,self.assertRaisesRegex(RuntimeError,"cuota"):
            TextProvider({"ai_provider":"ollama"}).chat([],[])
        self.assertEqual(post.call_count,1)

    def test_capabilities_exclude_unconnected_and_generated_actions(self):
        from core.capabilities import available_tools
        declarations=[{"name":n} for n in ["auto_programmer","arca_invoice","get_current_time"]]
        result=available_tools(declarations,{"enabled_tools":["auto_programmer","arca_invoice"]})
        self.assertEqual([d["name"] for d in result],["get_current_time"])


class ConfigTests(unittest.TestCase):
    def test_partial_save_preserves_integration_keys(self):
        from memory import config_manager as config
        with tempfile.TemporaryDirectory() as temp,patch.object(config,"CONFIG_DIR",Path(temp)),patch.object(config,"CONFIG_FILE",Path(temp)/"keys.json"):
            config.save_api_keys({"extra":"preserve","gemini_api_key":"old"})
            config.save_api_keys({"gemini_api_key":"new"})
            self.assertEqual(config.load_api_keys(),{"extra":"preserve","gemini_api_key":"new"})
            self.assertFalse(list(Path(temp).glob("*.tmp")))

    def test_corrupt_configuration_not_overwritten(self):
        from memory import config_manager as config
        with tempfile.TemporaryDirectory() as temp,patch.object(config,"CONFIG_DIR",Path(temp)),patch.object(config,"CONFIG_FILE",Path(temp)/"keys.json"):
            config.CONFIG_FILE.write_text("{bad",encoding="utf-8")
            with self.assertRaises(ValueError):
                config.save_api_keys({"x":1})
            self.assertEqual(config.CONFIG_FILE.read_text(),"{bad")

    def test_generated_actions_are_imported_lazily(self):
        from core.lazy import LazyAction
        fn=LazyAction("actions.arca_invoice","arca_invoice")
        self.assertIsNone(fn._function)
        self.assertIn("Error",fn({"action":"generar"}))


class ExecutionTests(unittest.TestCase):
    def test_executor_refuses_excess_work_until_actual_completion(self):
        gate=threading.Event()
        executor=BoundedExecutor(max_workers=1,max_pending=1)
        future=executor.submit(lambda:gate.wait(2))
        with self.assertRaises(RuntimeError):
            executor.submit(lambda:None)
        gate.set();future.result(timeout=3)
        self.assertEqual(executor.submit(lambda:7).result(timeout=3),7)
        executor.shutdown()

    def test_git_status_uses_real_repository(self):
        from actions.git_control import git_control
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(["git","init",temp],capture_output=True,check=True)
            Path(temp,"sample.txt").write_text("hello")
            result=git_control({"action":"status","repo_path":temp})
            self.assertIn("sample.txt",result)

    def test_google_missing_auth_cannot_report_success(self):
        from core import google_services
        from actions.gmail_control import gmail_control
        with tempfile.TemporaryDirectory() as temp,patch.object(google_services,"ROOT",Path(temp)):
            result=gmail_control({"action":"inbox"})
        self.assertIn("Error",result);self.assertIn("no está conectado",result)

    def test_maps_uses_encoded_real_url(self):
        from actions.google_maps import google_maps
        with patch("webbrowser.open",return_value=True) as browser:
            result=google_maps({"action":"directions","origin":"Bogotá","destination":"Cali","mode":"walk"})
        self.assertIn("travelmode=walking",browser.call_args.args[0]);self.assertIn("Mapa abierto",result)


if __name__=="__main__":
    unittest.main()
