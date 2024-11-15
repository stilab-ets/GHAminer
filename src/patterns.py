import re

framework_regex = {
    "pytest": re.compile(r"(?:(\d+)\s+passed)?(?:, )?(?:(\d+)\s+failed)?(?:, )?(?:(\d+)\s+skipped)?"),
    "Jest": re.compile(r"Tests: (\d+) total, (\d+) passed, (\d+) failed, (\d+) skipped"),
    "junit-gradle": re.compile(r"Passed: (\d+), Failed: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "rspec": re.compile(r"(\d+) examples?, (\d+) failures?(?:, (\d+) pending)?"),
    "PHPUnit": re.compile(r"Tests: (\d+), Assertions: (\d+), Failures: (\d+), Skipped: (\d+)"),
    "NUnit": re.compile(r"Total tests: (\d+) - Passed: (\d+), Failed: (\d+), Skipped: (\d+)"),
    "Go test": re.compile(r"PASS: (\d+), FAIL: (\d+), SKIP: (\d+)"),
    "junit-maven": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "cucumber-ruby": re.compile(
        r"(\d+) scenarios? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)[\s\S]*?(\d+) steps? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)"),
    "Cucumber-Java": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "testunit": re.compile(
        r"(\d+) tests, (\d+) assertions, (\d+) failures, (\d+) errors, (\d+) pendings, (\d+) omissions, (\d+) notifications")
}