## Testing

All functionality should have test coverage</br>
Test coverage means:
* Verifying that functionality works with the default case as well as some common cases
* Verifying that when provided broken/incorrect scenarios, features fail in the expected way, gracefully handling the error, but making it clear there was a failure
* All branches of code are tested so that no runtime errors happen by using the tool with common arguments/input

### How to run tests

From xa-scale folder:</br>
`python -m _test`

From VS Code (or another editor):</br>
Edit your debug/launch config to call the _test folder as a module

Optionally, place `run_all_tests` function from _test/testing_utils.py into your test file and run that file directly

### How to write tests

Files should be based on the very high level concepts, mostly equivalent to the folder structure, but breaking apart any large functionality

Functions should be based on the feature, mostly equivalent to medium size functions, but maybe a superset or subset of functions depending on the feature

Function examples:
* datetime/str formatting functions should be grouped into one test function
* config merging and loading functionality should be split apart into two functions because they are so complex

File examples:
* Core contains much of the entire core folder, but config and workload features are so big they are split apart
* Infra contains the entire infra folder because none of the infra functionality should be extremely complex to debug. If it is, it should be split apart