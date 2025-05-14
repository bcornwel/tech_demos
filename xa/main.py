#!/usr/bin/python3
 
from core.definitions import Flags


def help():
    print("Usage: xa-scale [preferred route] <args for route>")
    print("c|container: Deploy container")
    print("w|workload: Run workload")
    print("g|generate: Generate workload")
    print("r|run: Run main application")
    print("x|execute|listen: Run in listen mode")
    print("Examples: `xa-scale c build`, `xa-scale w nst`, `xa-scale g nst`, `xa-scale r`, `xa-scale x`")


if __name__ == "__main__":
    try:
        import sys
        if not len(sys.argv) > 1:
            help()
            raise Exception("No arguments provided, exiting")
        route = sys.argv[1]
        # set arguments as sys.argv[2:] to skip this file's routing
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        if route == "c" or route == "container":
            from container.deploy import main
            print(f"Running container functionality: {sys.argv[1]}")
            main()
        elif route == "w" or route == "workload":
            from core.workload import run_workload
            print(f"Running workload: {sys.argv[1]}")
            args = [arg for arg in sys.argv[1:] if '=' not in arg]
            kwargs = {arg.split('=')[0]: arg.split('=')[1] for arg in sys.argv[1:] if '=' in arg}
            run_workload(sys.argv[1])
        elif route == 'g' or route == 'generate':
            from core.workload import generate_workload
            msg = f"Generating workload: {sys.argv[1]}"
            if len(sys.argv) > 2:
                msg += f", copying files from {sys.argv[2]}"
            if len(sys.argv) > 3:
                msg += f", using example {sys.argv[3]} for config and flow"
            if len(sys.argv) > 4:
                msg += f", in test mode"
            print(msg)
            args = [arg for arg in sys.argv[1:] if '=' not in arg]
            kwargs = {arg.split('=')[0]: arg.split('=')[1] for arg in sys.argv[1:] if '=' in arg}
            generate_workload(*args, **kwargs)
        elif route == 'r' or route == 'run':
            from core.main import main
            print("Running XA-Scale")
            main()
        elif route == 'x' or route == "execute" or route == "listen":
            from infra.net_utils import listen_mode
            print(f"Running in listen mode")
            listen_mode()
        else:
            print(f"Invalid route: '{route}'")
    except Exception as e:
        if Flags.Debug:
            raise e
        else:
            print(e)
    