"""_chrome_launch.py — Clean Chrome launcher helper."""
import subprocess
import webbrowser

def chrome_launch(url: str) -> bool:
    """Launch the default system browser pointing to the specified URL."""
    try:
        # Launch default system browser (e.g. Comet, Chrome, Edge)
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        try:
            import subprocess
            subprocess.Popen(f'start "" "{url}"', shell=True)
            return True
        except:
            return False
