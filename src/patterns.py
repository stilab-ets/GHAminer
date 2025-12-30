import re

framework_regex = {
    # ==================== PYTHON ====================
    # pytest: "===== 5 passed, 2 failed, 1 skipped in 1.23s ====="
    "pytest": re.compile(r"(?:(\d+)\s+passed)?(?:, )?(?:(\d+)\s+failed)?(?:, )?(?:(\d+)\s+skipped)?"),
    # pytest alternative format with errors: "5 passed, 2 failed, 1 error, 1 skipped"
    "pytest-verbose": re.compile(r"=+\s*(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+error)?(?:,?\s*(\d+)\s+skipped)?.*?(?:in\s+[\d.]+s)?\s*=+"),
    # unittest: "Ran 10 tests in 0.001s" + "OK" or "FAILED (failures=2, errors=1)"
    "unittest": re.compile(r"Ran\s+(\d+)\s+tests?.*?(?:OK|FAILED\s*\((?:failures=(\d+))?(?:,?\s*errors=(\d+))?(?:,?\s*skipped=(\d+))?\))"),
    # nose/nose2: "Ran 10 tests in 0.5s" + "OK (SKIP=2)" or "FAILED (errors=1, failures=2)"
    "nose": re.compile(r"Ran\s+(\d+)\s+tests?.*?(?:OK(?:\s*\((?:SKIP=(\d+))?\))?|FAILED\s*\((?:errors=(\d+))?(?:,?\s*failures=(\d+))?(?:,?\s*skipped=(\d+))?\))"),
    # tox summary: "py39: commands succeeded" or "py39: FAIL"
    "tox": re.compile(r"(\w+):\s+(commands\s+succeeded|FAIL)"),

    # ==================== JAVASCRIPT/TYPESCRIPT ====================
    # Jest: "Tests: 5 passed, 2 failed, 7 total" or "Tests: 1 skipped, 5 passed, 6 total"
    "Jest": re.compile(r"Tests: (\d+) total, (\d+) passed, (\d+) failed, (\d+) skipped"),
    # Jest alternative format
    "Jest-alt": re.compile(r"Tests:\s+(?:(\d+)\s+skipped,?\s*)?(?:(\d+)\s+passed,?\s*)?(?:(\d+)\s+failed,?\s*)?(\d+)\s+total"),
    # Vitest: "Tests 5 passed | 2 failed | 1 skipped (8)"
    "vitest": re.compile(r"Tests\s+(?:(\d+)\s+passed)?\s*\|?\s*(?:(\d+)\s+failed)?\s*\|?\s*(?:(\d+)\s+skipped)?\s*\((\d+)\)"),
    # Vitest alternative: "✓ 5 tests passed" "× 2 tests failed"
    "vitest-alt": re.compile(r"[✓√]\s*(\d+)\s+tests?\s+passed|[×✗]\s*(\d+)\s+tests?\s+failed"),
    # Mocha: "5 passing (1s)" "2 failing" "1 pending"
    "mocha": re.compile(r"(\d+)\s+passing.*?(?:(\d+)\s+failing)?.*?(?:(\d+)\s+pending)?"),
    # Jasmine: "5 specs, 2 failures, 1 pending spec"
    "jasmine": re.compile(r"(\d+)\s+specs?,\s*(\d+)\s+failures?(?:,\s*(\d+)\s+pending)?"),
    # AVA: "5 tests passed" "2 tests failed" "1 test skipped"
    "ava": re.compile(r"(\d+)\s+tests?\s+passed|(\d+)\s+tests?\s+failed|(\d+)\s+tests?\s+skipped"),
    # Tap/Node-tap: "# pass 5" "# fail 2" "# skip 1"
    "tap": re.compile(r"#\s+pass\s+(\d+)|#\s+fail\s+(\d+)|#\s+skip\s+(\d+)|#\s+todo\s+(\d+)"),
    # Playwright: "5 passed (10s)" or "5 passed 2 failed (10s)"
    "playwright": re.compile(r"(\d+)\s+passed(?:\s+(\d+)\s+failed)?(?:\s+(\d+)\s+skipped)?"),
    # Cypress: "Tests: 5, Passing: 3, Failing: 2, Pending: 0, Skipped: 0"
    "cypress": re.compile(r"Tests:\s*(\d+),\s*Passing:\s*(\d+),\s*Failing:\s*(\d+)(?:,\s*Pending:\s*(\d+))?(?:,\s*Skipped:\s*(\d+))?"),

    # ==================== JAVA ====================
    # JUnit with Gradle: "Passed: 5, Failed: 2, Errors: 1, Skipped: 0"
    "junit-gradle": re.compile(r"Passed: (\d+), Failed: (\d+), Errors: (\d+), Skipped: (\d+)"),
    # JUnit with Maven Surefire: "Tests run: 10, Failures: 2, Errors: 1, Skipped: 0"
    "junit-maven": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
    # TestNG: "Total tests run: 10, Passes: 8, Failures: 2, Skips: 0"
    "testng": re.compile(r"Total tests run:\s*(\d+),\s*(?:Passes|Successes):\s*(\d+),\s*Failures:\s*(\d+),\s*Skips:\s*(\d+)"),
    # TestNG alternative: "===============================================\nTotal tests run: 10, Failures: 2, Skips: 1"
    "testng-alt": re.compile(r"Total tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Skips:\s*(\d+)"),
    # Spock: "5 tests completed, 2 failed, 1 skipped"
    "spock": re.compile(r"(\d+)\s+tests?\s+completed,\s*(\d+)\s+failed(?:,\s*(\d+)\s+skipped)?"),
    # Cucumber-Java: same as maven surefire
    "Cucumber-Java": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),

    # ==================== RUBY ====================
    # RSpec: "10 examples, 2 failures, 1 pending"
    "rspec": re.compile(r"(\d+) examples?, (\d+) failures?(?:, (\d+) pending)?"),
    # Minitest: "10 runs, 15 assertions, 2 failures, 1 errors, 0 skips"
    "minitest": re.compile(r"(\d+)\s+runs?,\s*(\d+)\s+assertions?,\s*(\d+)\s+failures?,\s*(\d+)\s+errors?,\s*(\d+)\s+skips?"),
    # Test::Unit: "10 tests, 15 assertions, 2 failures, 1 errors, 0 pendings, 0 omissions, 0 notifications"
    "testunit": re.compile(
        r"(\d+) tests, (\d+) assertions, (\d+) failures, (\d+) errors, (\d+) pendings, (\d+) omissions, (\d+) notifications"),
    # Cucumber-Ruby scenarios and steps
    "cucumber-ruby": re.compile(
        r"(\d+) scenarios? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)[\s\S]*?(\d+) steps? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)"),

    # ==================== .NET / C# ====================
    # NUnit: "Total tests: 10 - Passed: 8, Failed: 2, Skipped: 0"
    "NUnit": re.compile(r"Total tests: (\d+) - Passed: (\d+), Failed: (\d+), Skipped: (\d+)"),
    # NUnit v3 console: "Test Count: 10, Passed: 8, Failed: 2, Warnings: 0, Inconclusive: 0, Skipped: 0"
    "nunit-v3": re.compile(r"Test Count:\s*(\d+),\s*Passed:\s*(\d+),\s*Failed:\s*(\d+)(?:,\s*Warnings:\s*(\d+))?(?:,\s*Inconclusive:\s*(\d+))?(?:,\s*Skipped:\s*(\d+))?"),
    # xUnit: "Total: 10, Errors: 1, Failed: 2, Skipped: 0, Time: 1.234s"
    "xunit": re.compile(r"Total:\s*(\d+),\s*Errors:\s*(\d+),\s*Failed:\s*(\d+),\s*Skipped:\s*(\d+)"),
    # MSTest / dotnet test: "Passed! - Failed: 0, Passed: 10, Skipped: 0, Total: 10"
    "mstest": re.compile(r"(?:Passed!|Failed!)\s*-\s*Failed:\s*(\d+),\s*Passed:\s*(\d+),\s*Skipped:\s*(\d+),\s*Total:\s*(\d+)"),
    # dotnet test summary: "Total tests: 10. Passed: 8. Failed: 2. Skipped: 0."
    "dotnet-test": re.compile(r"Total tests:\s*(\d+)\.\s*Passed:\s*(\d+)\.\s*Failed:\s*(\d+)\.\s*Skipped:\s*(\d+)"),

    # ==================== GO ====================
    # Go test: "ok   package 0.005s" or "FAIL package 0.005s"
    "Go test": re.compile(r"PASS: (\d+), FAIL: (\d+), SKIP: (\d+)"),
    # Go test verbose: "--- PASS: TestName (0.00s)" "--- FAIL: TestName (0.00s)" "--- SKIP: TestName (0.00s)"
    "go-test-verbose": re.compile(r"---\s+(PASS|FAIL|SKIP):\s+\w+"),
    # Go test summary: "PASS" or "FAIL" followed by coverage
    "go-test-summary": re.compile(r"^(PASS|FAIL)$|coverage:\s*([\d.]+)%"),
    # Go test with gotestsum: "DONE 10 tests in 1.234s"
    "gotestsum": re.compile(r"DONE\s+(\d+)\s+tests?\s+(?:,\s*(\d+)\s+skipped\s+)?in"),
    # Go test2json / gotestsum json: count PASS/FAIL/SKIP actions
    "go-json": re.compile(r'"Action":\s*"(pass|fail|skip)"'),

    # ==================== RUST ====================
    # Cargo test: "test result: ok. 10 passed; 2 failed; 1 ignored; 0 measured; 0 filtered out"
    "cargo-test": re.compile(r"test result:\s*(?:ok|FAILED)\.\s*(\d+)\s+passed;\s*(\d+)\s+failed;\s*(\d+)\s+ignored(?:;\s*(\d+)\s+measured)?"),
    # Cargo test alternative: "10 passed; 2 failed; 1 ignored"
    "cargo-test-alt": re.compile(r"(\d+)\s+passed;\s*(\d+)\s+failed;\s*(\d+)\s+ignored"),

    # ==================== PHP ====================
    # PHPUnit: "Tests: 10, Assertions: 15, Failures: 2, Skipped: 1"
    "PHPUnit": re.compile(r"Tests: (\d+), Assertions: (\d+), Failures: (\d+), Skipped: (\d+)"),
    # PHPUnit alternative: "OK (10 tests, 15 assertions)"
    "phpunit-ok": re.compile(r"OK\s*\((\d+)\s+tests?,\s*(\d+)\s+assertions?\)"),
    # PHPUnit failures: "FAILURES! Tests: 10, Assertions: 15, Failures: 2, Errors: 1."
    "phpunit-fail": re.compile(r"FAILURES!\s*Tests:\s*(\d+),\s*Assertions:\s*(\d+)(?:,\s*Failures:\s*(\d+))?(?:,\s*Errors:\s*(\d+))?"),
    # Pest (PHP): "Tests: 10 passed, 2 failed"
    "pest": re.compile(r"Tests:\s*(\d+)\s+passed(?:,\s*(\d+)\s+failed)?"),
    # Codeception: "OK (10 tests, 15 assertions)"
    "codeception": re.compile(r"(?:OK|FAILURES!)\s*\((\d+)\s+tests?,\s*(\d+)\s+assertions?\)"),

    # ==================== SWIFT ====================
    # XCTest: "Test Suite 'All tests' passed at 2021-01-01." "Executed 10 tests, with 2 failures (1 unexpected) in 1.234 (1.234) seconds"
    "xctest": re.compile(r"Executed\s+(\d+)\s+tests?,\s*with\s+(\d+)\s+failures?\s*(?:\((\d+)\s+unexpected\))?\s*in"),
    # swift test: "Test Suite 'PackageTests' passed at" + result summary
    "swift-test": re.compile(r"Test Suite.*(?:passed|failed).*Executed\s+(\d+)\s+tests?,\s*with\s+(\d+)\s+failures?"),

    # ==================== KOTLIN ====================
    # Kotest: "10 tests completed, 2 failed, 1 ignored"
    "kotest": re.compile(r"(\d+)\s+tests?\s+completed,\s*(\d+)\s+failed(?:,\s*(\d+)\s+ignored)?"),

    # ==================== SCALA ====================
    # ScalaTest: "All tests passed." or "*** 2 TESTS FAILED ***"
    "scalatest": re.compile(r"(\d+)\s+tests?,.*?(\d+)\s+(?:succeeded|passed),.*?(\d+)\s+failed"),
    # sbt test: "Total 10, Failed 2, Errors 0, Passed 8, Skipped 0"
    "sbt-test": re.compile(r"Total\s+(\d+),\s*Failed\s+(\d+),\s*Errors\s+(\d+),\s*Passed\s+(\d+)(?:,\s*Skipped\s+(\d+))?"),
    # specs2: "10 examples, 2 failures, 1 error"
    "specs2": re.compile(r"(\d+)\s+examples?,\s*(\d+)\s+failures?(?:,\s*(\d+)\s+errors?)?"),

    # ==================== ELIXIR ====================
    # ExUnit: "10 tests, 2 failures" or "10 tests, 0 failures, 1 skipped"
    "exunit": re.compile(r"(\d+)\s+tests?,\s*(\d+)\s+failures?(?:,\s*(\d+)\s+(?:skipped|excluded))?"),

    # ==================== C/C++ ====================
    # Google Test: "[  PASSED  ] 10 tests." "[  FAILED  ] 2 tests."
    "gtest": re.compile(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests?|\[\s*FAILED\s*\]\s*(\d+)\s+tests?"),
    # Google Test summary: "10 tests from 5 test suites ran." + "[  PASSED  ] 8 tests." + "[  FAILED  ] 2 tests."
    "gtest-summary": re.compile(r"(\d+)\s+tests?\s+from\s+(\d+)\s+test\s+(?:suites?|cases?)\s+ran"),
    # Catch2: "All tests passed (10 assertions in 5 test cases)"
    "catch2": re.compile(r"(?:All tests passed|test cases:.*?(\d+)\s+passed.*?(\d+)\s+failed).*?\((\d+)\s+assertions?"),
    # Catch2 alternative: "test cases: 10 | 8 passed | 2 failed"
    "catch2-alt": re.compile(r"test cases:\s*(\d+)\s*\|\s*(\d+)\s+passed\s*\|\s*(\d+)\s+failed"),
    # CTest: "100% tests passed, 0 tests failed out of 10"
    "ctest": re.compile(r"(\d+)%\s+tests\s+passed,\s*(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)"),
    # Boost.Test: "*** No errors detected" or "*** 2 failures are detected in 10 test cases"
    "boost-test": re.compile(r"\*\*\*\s*(?:No errors detected|(\d+)\s+failures?\s+(?:is|are)\s+detected\s+in\s+(\d+)\s+test\s+cases?)"),

    # ==================== FLUTTER/DART ====================
    # Flutter test: "00:05 +10: All tests passed!" or "00:05 +8 -2: Some tests failed."
    "flutter-test": re.compile(r"\+(\d+)(?:\s+-(\d+))?(?:\s+~(\d+))?:\s+(?:All tests passed|Some tests failed)"),
    # Dart test: "00:01 +10: All tests passed!"
    "dart-test": re.compile(r"\+(\d+)(?:\s+-(\d+))?:\s+All tests passed"),

    # ==================== ANDROID ====================
    # Android Instrumentation: "OK (10 tests)"
    "android-instrumentation": re.compile(r"OK\s*\((\d+)\s+tests?\)|Tests run:\s*(\d+),\s*Failures:\s*(\d+)"),

    # ==================== GRADLE GENERIC ====================
    # Gradle test task: "> Task :test" followed by results
    "gradle-test": re.compile(r"(\d+)\s+tests?\s+completed,\s*(\d+)\s+failed(?:,\s*(\d+)\s+skipped)?"),

    # ==================== GENERIC CI PATTERNS ====================
    # Generic passed/failed pattern
    "generic": re.compile(r"(\d+)\s+(?:tests?\s+)?passed|(\d+)\s+(?:tests?\s+)?failed|(\d+)\s+(?:tests?\s+)?skipped"),
}