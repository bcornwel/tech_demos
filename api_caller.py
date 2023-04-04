import api
import subprocess

if __name__ == "__main__":
    print("starting runner")
    runner = api.APIRunner()
    print("running direct commands")
    runner.do_hl_cmd("some data")
    runner.do_ll_cmd("some other data")
    runner.do_ll_kw_cmd(kw1="some other data")
    # print("running external commands")
    # runner.run_command("stop")
    # runner.run_command("trigger_segfault")
    runner.run_command("stop")    
