import faulthandler
import runpy

faulthandler.dump_traceback_later(25, exit=True)
runpy.run_path(r"C:\Python3.12venv\chipwhisperer\chipwhisperer-jupyter\peters\dump_flash_target.py",
               run_name="__main__")
