"""
This file tests the code quality of the entire package
"""


def test_imports_and_docstrings():
    """
    Tests all functions and files for proper documentation and import behavior
    This function will take a while but is very thorough in catching quality bugs before they hit the main branch
    """
    from inspect import getmembers, isfunction, isclass
    import os
    import re
    from typing import Callable

    from core.definitions import Directories
    from infra.file_utils import safe_path, import_module_from_path, get_project_root

    arg_exceptions = [
                        "self", "cls",  # don't need documentation for reflective class/obj references
                    ]
    func_exceptions = []
    class_exceptions = ["Logger"]
    method_exceptions = [
                            "_generate_next_value_",  # undocumented enum function
                        ]
    class_method_exceptions = [
                                "ArgumentParser",  # child class of an external class with several undocumented methods
                                "TailLogHandler",  # child class of an external class with several undocumented methods
                                "ConsoleLogHandler",  # child class of an external class with several undocumented methods
                              ]
    module_doc_exceptions = ["__main__", "__init__"]
    module_import_exceptions = []
    module_main_section_exceptions = ["__main__", "__init__",]
    resource_manager_exceptions = ["utils", "test_code_quality"]
    excluded_files = [Directories.Test, Directories.Results]


    def get_py_files():
        schema_path = safe_path(get_project_root(), relative=False)
        for file in schema_path.rglob("*/*.py"):
            yield file
            
    def test_func_docstring(func:Callable) -> str:
        """
        Ensures a function's docstring is in good form (has a body, has correct args, and has arg data filled out)

        Args:
            func (Callable): the function to check

        Returns:
            str: issues with the docstring
        """
        doc = func.__doc__
        assert doc and len(doc), f"{func.__globals__['__name__']}.{func.__name__} does not have a docstring!"  # this is critical, can't continue otherwise
        if "_description_" in doc:
            yield f"{func.__globals__['__name__']}.{func.__name__} is missing at least one argument description!"
        if "_summary_" in doc:
            yield f"{func.__globals__['__name__']}.{func.__name__} does not have a summary!"
        varnames = list(func.__code__.co_varnames[:func.__code__.co_argcount])
        if len(varnames):
            if varnames[0] in arg_exceptions:
                varnames.pop(0)
            for var in varnames:
                if var not in doc:
                    yield f"'{var}' is not described in {func.__globals__['__name__']}.{func.__name__}'s docstring!"
        if re.search(r":( )*param( )*(\w)*( )*:", doc) or re.search(r":( )*raises( )*(\w)*( )*:", doc) or re.search(r":( )*returns( )*(\w)*( )*:", doc):
            yield f"'It appears the docstring for {func.__globals__['__name__']}.{func.__name__}'s is reST formatted instead of the Google docstring style!"
        if re.search(r"Parameters(\n)*(\t)*( )*----------", doc) or re.search(r"Returns(\n)*(\t)*( )*----------", doc) or re.search(r"Raises(\n)*(\t)*( )*----------", doc):
            yield f"'It appears the docstring for {func.__globals__['__name__']}.{func.__name__}'s is Numpy formatted instead of the Google docstring style!"
        if re.search(r"@( )*param( )*(\w)*( )*:", doc) or re.search(r"@( )*raise( )*(\w)*( )*:", doc) or re.search(r"@( )*return( )*(\w)*( )*:", doc):
            yield f"'It appears the docstring for {func.__globals__['__name__']}.{func.__name__}'s is Epytext formatted instead of the Google docstring style!"

    
    def test_class_docstring(cls) -> str:
        """
        Ensures a class' docstring is in good form (has a body)

        Returns:
            str: _description_

        Yields:
            Iterator[str]: _description_
        """
        if not cls.__doc__ or not len(cls.__doc__):
            yield f"{cls.__module__}.{cls.__name__} does not have a docstring!"
        # methods = [m[1] for m in getmembers(cls, isfunction) if not re.match(r"__\w+__", m[1].__name__)]  # this method wasn't catching classmethods
        methods = [v for v in vars(cls).values() if (isinstance(v, classmethod) or isfunction(v)) and not re.match(r"__\w+__", v.__name__)]
        if f"{cls.__name__}" not in class_method_exceptions:
            for method in methods:
                if f"{method.__name__}" not in method_exceptions:
                    for issue in test_func_docstring(method):
                        yield issue

    def test_module_docstring(mod):
        assert mod.__doc__ and len(mod.__doc__), f"{mod.__name__} does not have a docstring!"

    def check_for_main(code, file):
        """
        Checks file internals for expected and banned code

        Args:
            code (str): the code to analyze
            file (str): the file name
        """
        # check that all files have a main
        match = re.findall(r"if __name__ == ['\"]__main__['\"]", code)
        assert match, f"{file} does not have a main section, would run on import!"


    def check_for_resource_manager(code, file):
        """
        checks to ensure nobody is using unsanctioned threading functionality

        Args:
            code (str): the code to analyze
            file (str): the file name
        """
        # now check for references that should use ResourceManager instead
        match = re.findall(r"ThreadPoolExecutor", code)
        assert not match, f"{file} includes a reference to ThreadPoolExecutor! Use ResourceManager from framework.resource_manager instead!"
        match = re.findall(r"ProcessPoolExecutor", code)
        assert not match, f"{file} includes a reference to ProcessPoolExecutor! Use ResourceManager from framework.resource_manager instead!"
        match = re.findall(r"threading.Thread", code)
        assert not match, f"{file} includes a reference to threading.Thread! Use ResourceManager from framework.resource_manager instead!"

    try:
        schema_path = safe_path(get_project_root())
        cwd = os.getcwd()
        os.chdir(schema_path)
        accumulated_errors = set()
        py_files = [file for file in get_py_files() if not any(exclude in str(file) for exclude in excluded_files)]
        for i, py_file in enumerate(py_files):
            with open(py_file, 'r') as f:
                py_code = f.read()
            try:
                if f"{os.path.basename(py_file)[:-3]}" not in module_main_section_exceptions:
                    check_for_main(py_code, py_file)
            except Exception as internals_error:
                accumulated_errors.add(f"{py_file}: {internals_error}")
            try:
                if f"{os.path.basename(py_file)[:-3]}" not in resource_manager_exceptions:
                    check_for_resource_manager(py_code, py_file)
            except Exception as internals_error:
                accumulated_errors.add(f"{py_file}: {internals_error}")
            try:
                if f"{os.path.basename(py_file)[:-3]}" not in module_import_exceptions:
                    file_mod = import_module_from_path(py_file)
            except Exception as import_error:
                accumulated_errors.add(f"{py_file}: {import_error}")
            try:
                if not any(mod in f"{py_file}" for mod in module_doc_exceptions):  # this file can't be imported because it will execute so we have to ignore it
                    test_module_docstring(file_mod)
            except Exception as module_docstring_error:
                accumulated_errors.add(f"{py_file}: {module_docstring_error}")

            base_name = os.path.basename(py_file)[:-3]
            # funcs = [func[1] for func in getmembers(file_mod, isfunction) if func[1].__globals__['__name__'] == base_name]  # this function wasn't as performant
            funcs = [v for v in vars(file_mod).values() if isfunction(v) and v.__globals__['__name__'] == base_name]
            for item in funcs:
                try:
                    if f"{item.__globals__['__name__']}" not in func_exceptions:
                        for issue in test_func_docstring(item):  # test_func_docstring is a generator function, yields errors
                            accumulated_errors.add(f"{py_file}: {issue}")
                except Exception as func_docstring_error:
                    accumulated_errors.add(f"{py_file}: {func_docstring_error}")
            classes = [c[1] for c in getmembers(file_mod, isclass) if c[1].__module__ == base_name]
            for item in classes:
                try:
                    if item.__name__ not in class_exceptions:
                        for issue in test_class_docstring(item):  # test_class_docstring is a generator function, yields errors
                            accumulated_errors.add(f"{py_file}: {issue}")
                except Exception as class_docstring_error:
                    accumulated_errors.add(f"{py_file}: {class_docstring_error}")
        os.chdir(cwd)  # go back to original dir
    except Exception as import_and_docstring_error:
        print(import_and_docstring_error)
        os.chdir(cwd)  # go back to original dir
        raise import_and_docstring_error
    if len(accumulated_errors) > 0:
        raise Exception(f"{len(accumulated_errors)} code quality errors were found. Please adress the following items\n" + 'V'*20 + '\n' + '\n'.join(accumulated_errors) + '\n' + '^'*20 + f"\n{len(accumulated_errors)} code quality errors were found. Please adress the above items.\nIf you believe there are exceptions, edit the exception lists in test_code_quality.test_imports_and_docstrings")

if __name__ == "__main__":
    from core.definitions import Strings
    print(Strings.NotStandalone)