import os

func_doc_threshold = 50  # how many lines require a definition for a function
class_doc_threshold = 20  # how many lines require a definition for a class
breakup_threshold = 200  # how many lines before a function should be broken up
breakup_exceptions = []
dir_exceptions = ["__pycache__", "marsenv"]

def should_break(text, name, i, n):
    if len(name):
        if i-n > breakup_threshold and name not in breakup_exceptions:
            print(f"\tBreak up function {name} because it's {i-n} lines long")

def should_doc(text, name, i, n, is_class):
    if len(name):
        if '"""' not in text[n+1]:
            if is_class and i-n > 20:  # does not start with a docstring
                print(f"\tclass {name} needs docstring because it's {i-n} lines long")
            elif i-n > func_doc_threshold:
                print(f"\tfunction {name} needs docstring because it's {i-n} lines long")

def walk(d):
    #print(f"Walking {d}")
    files = os.listdir(d)
    for fi in files:  # gets the files/folders in a dir
        full_path = os.path.join(d, fi)
        if fi.endswith(".py"):
            print(f"Analyzing {full_path}")
            with open(full_path, 'r') as f_code:
                func_name = ""
                class_name = ""
                func_start = 0
                class_start = 0
                text = f_code.readlines()
                for i, line in enumerate(text):  # for loop over the .py text with line numbers
                    line = line.strip()  # remove leading and trailing whitespace (tab, space, newline)
                    if line.startswith("def "):  # denotes a function detected
                        should_doc(text, func_name, i, func_start, is_class=False)  # check if should document the function
                        should_break(text, func_name, i, func_start)  # check if the function should be broken up
                        func_name = line[4:line.find("(")]  # get function name between def and ():
                        func_start = i
                    elif line.startswith("class "):
                        should_doc(text, class_name, i, class_start, is_class=True)  # check if should document the class
                        class_name = line[6:line.find(":")]  # get a class name between class and :
                        class_start = i
        elif "." not in fi and fi not in dir_exceptions:
            try:
                walk(full_path)  # walk the sub dir
            except Exception as walk_dir_exception:
                exc_msg = f"{walk_dir_exception}"
                if "directory name is invalid" in exc_msg:
                    pass
                else:
                    print(f"Could not open {full_path}. Is it a directory??: {walk_dir_exception}")

walk(os.getcwd())  # walk current directory
