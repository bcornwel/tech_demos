class Directories:
    Configs = "configs"  # where config files are generally stored
    Docs = "docs"  # where documentation is stored
    Schemas = "schemas"  # where schemas are stored
    Test = "_test"  # where test files are stored
    VirtualEnv = "env"  # folder for virtual environment data


class ExitCodes:
    Okay = 0
    Err = 1
    ErrNoLog = 2


class FileNames:
    ActionMap = "action_map.json"  # the file containing the errnames:action mapping
    ErrorMap = "error_map.json"  # the file containing the syscheck errors:errnames mapping
    InterventionData = "intervention_data.json"  # the file containing interventions to be applied
    HealingResults = "healing_results.json"  # the file containing results of the self-healing interventions
    SysCheckResults = "result.log"  # the file containing the high level syscheck result data
    ResultMap = "result_map.json"  # the file containing the test names:results mapping
    LogName = "healing.log"
    ErrorLogName = "errors.log"


class KeyNames:
    Action = "action"
    File = "file"
    Header = "header"
    Input = "input"
    Output = "output"
    Result = "Result"
    Test = "Test"


class Networking:
    ResponseTimeout = 5
    HttpProxy = "http://proxy-dmz.intel.com:911"
    HttpsProxy = "http://proxy-dmz.intel.com:912"


class RegexStrings:
    """
    Contains useful regex strings
    all regex string unless one-off tests should be located here
    """
    Alpha = r"[a-zA-Z]+"
    AlphaNumeric = r"[a-zA-Z\.0-9]+"
    AlphaNumericWithSpace = r"[a-zA-Z\.0-9 ]+"
    BlockDelete = r"(?i)Delete from"
    BlockDrop = r"(?i)Drop (index|constraint|table|column|primary|foreign|check|database|view)"
    BlockSqlComment = r"--"
    Directory = r"([a-zA-Z]:\\\\)|(\/|\\|\\\\){0,1}(\w+(\/|\\|\\\\))*\w+(\/|\\|\\\\)*"
    FriendlyName = r"[^a-zA-Z0-9_\- ]+"  # non-friendly name characters
    Numeric = r"(0-9)+\.*(0-9)+"
    PathLike = r"((?:[^;]*/)*)(.*)"
    PathTraversal = r"(/|\\|\\\\)\.\.(/|\\|\\\\)"
    PythonFile = r"([a-zA-Z]:){0,1}(/|\\|\\\\){0,1}(\w+(/|\\|\\\\))*\w+\.py"
    SpaceDelimiter = r"[ ]{2,}"
    Tuple = r"[a-zA-Z0-9_\(\)\,]"
    Url = r"http(s){0,1}:\/\/(((([0-1]*[0-9]*[0-9]\.|2[0-5][0-5]\.){3})([0-1]*[0-9]*[0-9]|2[0-5][0-5])(:[0-9]{0,4}|[0-5][0-9]{4}|6[0-5][0-5][0-3][0-5])*)|((\d*[a-zA-Z][a-zA-Z0-9\.]*(\-*))+\.[a-zA-Z0-9]{1,3}))((/[\w\-\.]*)*(\?\w+=\w+)*)*"
    MarkdownLink = r"\[.*\]\(.*\)"
    Variable = r"[\w\. ]+"
    AnsiEscapes = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"


class ResultDefinitions:
    ResultFilePass = "OK"
    ResultFileFail = "FAIL"
    TestFilePass = "PASSED"
    TestFileFail = "FAILED"


class Strings:
    NotStandalone = "This file is not meant to be run by itself, it should be imported"
    Contact = "brit.thornwell@intel.com"
    Version = "0.1"


if __name__ == "__main__":
    print(Strings.NotStandalone)
