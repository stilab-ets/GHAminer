import re
import requests
import base64
from request_github import get_request
import logging

import re

def count_dependencies(content, file_type):
    """
    Count the dependencies in the content based on the file type.
    Supports a wide range of dependency management files across different languages.
    """
    if content is None:
        return 0
        
    # ==================== JAVA ====================
    if file_type in ['pom.xml']:
        # Maven: count <dependency> tags
        dependency_pattern = re.compile(r'<dependency>')
        return len(dependency_pattern.findall(content))
    
    elif file_type in ['build.gradle', 'build.gradle.kts']:
        # Gradle: count implementation, compile, api, testImplementation, etc.
        dependency_pattern = re.compile(
            r'implementation\s*[\(\']|'
            r'compile\s*[\(\']|'
            r'api\s*[\(\']|'
            r'testImplementation\s*[\(\']|'
            r'testCompile\s*[\(\']|'
            r'runtimeOnly\s*[\(\']|'
            r'compileOnly\s*[\(\']|'
            r'annotationProcessor\s*[\(\']|'
            r'kapt\s*[\(\']'
        )
        return len(dependency_pattern.findall(content))
    
    # ==================== PYTHON ====================
    elif file_type == 'requirements.txt' or file_type.startswith('requirements'):
        # Each non-empty, non-comment line is a dependency
        return sum(1 for line in content.splitlines() 
                   if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('-'))
    
    elif file_type == 'pyproject.toml':
        # Poetry/PEP 621: look for dependencies list
        deps = re.findall(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        dev_deps = re.findall(r'dev-dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        optional_deps = re.findall(r'\[project\.optional-dependencies\.(.*?)\]', content, re.DOTALL)
        count = 0
        for dep_block in deps + dev_deps:
            count += len(re.findall(r'["\'][\w\-]+', dep_block))
        return count
    
    elif file_type == 'Pipfile':
        # Pipenv: count package entries
        packages = re.findall(r'^\s*[\w\-]+\s*=', content, re.MULTILINE)
        return len(packages)
    
    elif file_type == 'setup.py':
        # setuptools: look for install_requires
        deps = re.findall(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'["\'][\w\-]+', dep_block))
        return count
    
    elif file_type == 'environment.yml' or file_type == 'environment.yaml':
        # Conda: count dependencies
        deps = re.findall(r'^\s*-\s+[\w\-]', content, re.MULTILINE)
        return len(deps)
    
    # ==================== JAVASCRIPT/TYPESCRIPT ====================
    elif file_type == 'package.json':
        # NPM/Yarn: count all dependency types
        dep_sections = [
            r'"dependencies"\s*:\s*\{([^}]*)\}',
            r'"devDependencies"\s*:\s*\{([^}]*)\}',
            r'"peerDependencies"\s*:\s*\{([^}]*)\}',
            r'"optionalDependencies"\s*:\s*\{([^}]*)\}'
        ]
        count = 0
        for pattern in dep_sections:
            deps = re.findall(pattern, content, re.DOTALL)
            for dep_block in deps:
                # Count quoted package names
                count += len(re.findall(r'"[\w@/\-]+"\s*:', dep_block))
        return count
    
    # ==================== RUBY ====================
    elif file_type == 'Gemfile':
        # Bundler: count gem declarations
        return len(re.findall(r'^\s*gem\s+[\'"]', content, re.MULTILINE))
    
    # ==================== PHP ====================
    elif file_type == 'composer.json':
        # Composer: count require and require-dev
        dep_sections = [
            r'"require"\s*:\s*\{([^}]*)\}',
            r'"require-dev"\s*:\s*\{([^}]*)\}'
        ]
        count = 0
        for pattern in dep_sections:
            deps = re.findall(pattern, content, re.DOTALL)
            for dep_block in deps:
                count += len(re.findall(r'"[\w/\-]+"\s*:', dep_block))
        # Subtract php requirement if present
        if '"php"' in content:
            count = max(0, count - 1)
        return count
    
    # ==================== GO ====================
    elif file_type == 'go.mod':
        # Go modules: count require statements
        requires = re.findall(r'^\s*require\s*\(', content, re.MULTILINE)
        if requires:
            # Multi-line require block
            req_block = re.findall(r'require\s*\((.*?)\)', content, re.DOTALL)
            count = 0
            for block in req_block:
                count += len(re.findall(r'^\s*[\w\./\-]+\s+v', block, re.MULTILINE))
            return count
        else:
            # Single-line require statements
            return len(re.findall(r'^\s*require\s+[\w\./\-]+\s+v', content, re.MULTILINE))
    
    # ==================== RUST ====================
    elif file_type == 'Cargo.toml':
        # Cargo: count dependencies in all sections
        dep_sections = [
            r'\[dependencies\](.*?)(?=\[|\Z)',
            r'\[dev-dependencies\](.*?)(?=\[|\Z)',
            r'\[build-dependencies\](.*?)(?=\[|\Z)'
        ]
        count = 0
        for pattern in dep_sections:
            deps = re.findall(pattern, content, re.DOTALL)
            for dep_block in deps:
                # Count package = "version" or package = { ... } entries
                count += len(re.findall(r'^\s*[\w\-]+\s*=', dep_block, re.MULTILINE))
        return count
    
    # ==================== .NET ====================
    elif file_type.endswith('.csproj') or file_type.endswith('.fsproj') or file_type.endswith('.vbproj'):
        # NuGet: count PackageReference elements
        return len(re.findall(r'<PackageReference', content))
    
    elif file_type == 'packages.config':
        # Legacy NuGet
        return len(re.findall(r'<package\s', content))
    
    # ==================== SWIFT ====================
    elif file_type == 'Package.swift':
        # Swift Package Manager
        return len(re.findall(r'\.package\s*\(', content))
    
    elif file_type == 'Podfile':
        # CocoaPods
        return len(re.findall(r'^\s*pod\s+[\'"]', content, re.MULTILINE))
    
    elif file_type == 'Cartfile':
        # Carthage
        return len(re.findall(r'^\s*(?:github|git|binary)\s+[\'"]', content, re.MULTILINE))
    
    # ==================== SCALA ====================
    elif file_type == 'build.sbt':
        # SBT
        return len(re.findall(r'libraryDependencies\s*\+[+=]|"[\w\.\-]+"\s*%', content))
    
    # ==================== ELIXIR ====================
    elif file_type == 'mix.exs':
        # Mix
        deps = re.findall(r'defp?\s+deps\s+do(.*?)end', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'\{:[\w_]+', dep_block))
        return count
    
    # ==================== DART/FLUTTER ====================
    elif file_type == 'pubspec.yaml':
        # Pub
        dep_sections = re.findall(r'(?:dependencies|dev_dependencies):\s*((?:\n\s+[\w_]+:.*)+)', content)
        count = 0
        for section in dep_sections:
            count += len(re.findall(r'^\s+[\w_]+:', section, re.MULTILINE))
        return count
    
    # ==================== HASKELL ====================
    elif file_type.endswith('.cabal'):
        # Cabal
        return len(re.findall(r'^\s*build-depends:', content, re.MULTILINE))
    
    # ==================== CLOJURE ====================
    elif file_type == 'project.clj':
        # Leiningen
        deps = re.findall(r':dependencies\s*\[(.*?)\]', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'\[[\w\.\-/]+', dep_block))
        return count
    
    elif file_type == 'deps.edn':
        # deps.edn
        deps = re.findall(r':deps\s*\{(.*?)\}', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'[\w\.\-/]+\s*\{', dep_block))
        return count
    
    # ==================== C/C++ ====================
    elif file_type == 'vcpkg.json':
        # vcpkg
        deps = re.findall(r'"dependencies"\s*:\s*\[(.*?)\]', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'"[\w\-]+"', dep_block))
        return count
    
    elif file_type == 'conanfile.txt':
        # Conan (txt format)
        requires = re.findall(r'\[requires\](.*?)(?=\[|\Z)', content, re.DOTALL)
        count = 0
        for req_block in requires:
            count += len(re.findall(r'^\s*[\w\-]+/', req_block, re.MULTILINE))
        return count
    
    elif file_type == 'conanfile.py':
        # Conan (python format)
        return len(re.findall(r'requires\s*=|self\.requires\(', content))
    
    elif file_type == 'CMakeLists.txt':
        # CMake: count find_package and FetchContent
        find_packages = len(re.findall(r'find_package\s*\(', content))
        fetch_content = len(re.findall(r'FetchContent_Declare\s*\(', content))
        return find_packages + fetch_content
    
    # ==================== PERL ====================
    elif file_type == 'cpanfile':
        # cpanfile
        return len(re.findall(r'^\s*requires\s+[\'"]', content, re.MULTILINE))
    
    # ==================== R ====================
    elif file_type == 'DESCRIPTION':
        # R package DESCRIPTION
        deps = re.findall(r'(?:Depends|Imports|Suggests):\s*(.*?)(?=\n\w|\Z)', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'[\w\.]+', dep_block))
        return count
    
    # ==================== JULIA ====================
    elif file_type == 'Project.toml':
        # Julia
        deps = re.findall(r'\[deps\](.*?)(?=\[|\Z)', content, re.DOTALL)
        count = 0
        for dep_block in deps:
            count += len(re.findall(r'^\s*[\w]+\s*=', dep_block, re.MULTILINE))
        return count
    
    else:
        # Default for unsupported types
        return 0


import time
import requests
import logging

def get_github_actions_log(repo_full_name, run_id, token=None, max_retries=3):
    """
    Fetch the logs for a specific GitHub Actions workflow run.
    Handles binary (ZIP) responses correctly and retries on rate limits.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"token {token}"} if token else {}

    retries = 0  # Track retries

    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers, stream=True)  # Use raw binary stream
            
            if response.status_code == 200:
                return response.content  # Return raw binary log data
            
            elif response.status_code == 403:  # Rate limit exceeded
                rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                if rate_limit_reset:
                    wait_time = int(rate_limit_reset) - int(time.time()) + 1  # Ensure at least 1s wait
                    logging.warning(f"GitHub API rate limit exceeded. Sleeping for {wait_time} seconds...")
                    time.sleep(wait_time)  # Sleep until the rate limit resets
                else:
                    logging.warning("GitHub API rate limit hit but no reset time provided. Sleeping for 60s.")
                    #time.sleep(1)  # Default sleep time before retrying
                
            elif response.status_code == 404:
                logging.error(f"Logs for build {run_id} in {repo_full_name} were not found. They may have expired.")
                return None  # No point retrying if logs don't exist
            
            else:
                logging.info(f"logs data for run {run_id} in {repo_full_name} does not exist, Status: {response.status_code}")
                return None  # Other errors should not be retried
            
        except requests.exceptions.RequestException as err:
            logging.error(f"Unexpected error fetching logs for run {run_id} in {repo_full_name}: {err}")
        
        retries += 1
        logging.warning(f"Retrying log fetch for {repo_full_name}, run {run_id} (attempt {retries}/{max_retries})")
        time.sleep(5)  # Short delay before retrying

    logging.error(f"Failed to fetch logs after {max_retries} retries for run {run_id} in {repo_full_name}")
    return None  # Return None if all retries fail


    
def get_file_content(owner, repo, path, token=None):
    """
    Fetch the content of a file from a GitHub repository.
    Uses get_request to handle rate limits properly.
    Includes explicit error handling.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    try:
        response = get_request(url, token)
        if response and 'content' in response:
            return base64.b64decode(response['content']).decode('utf-8')
        else:
            logging.error(f"Failed to fetch file content for {path} in {owner}/{repo}")
            return None
    except base64.binascii.Error as decode_err:
        logging.error(f"Error decoding file content for {path} in {owner}/{repo}: {decode_err}")
        return None
    except Exception as err:
        logging.error(f"Unexpected error fetching file content for {path} in {owner}/{repo}: {err}")
        return None


def summarize_test_results(test_results):
    """
    Summarize the test results in the desired format.
    """
    summary = {
        'tr tests ok': test_results.get('passed', 0),
        'tr tests fail': test_results.get('failed', 0),
        'tr tests run': test_results.get('total', 0),
        'tr tests skipped': test_results.get('skipped', 0),
        'tr failed tests': []  # Optionally add the names of failed tests if available
    }
    return summary



def identify_test_frameworks(files, owner, repo, token=None):
    """
    Identify the test frameworks based on the presence of specific dependencies in build files.
    """
    test_framework_mapping = {
        # ==================== JAVA ====================
        'junit': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'junit5': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'testng': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'cucumber-java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'spock': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'mockito': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'assertj': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        
        # ==================== PYTHON ====================
        'pytest': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'setup.cfg', 'tox.ini'],
        'unittest': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'nose': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'nose2': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'hypothesis': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'behave': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'robot': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'tox': ['tox.ini', 'pyproject.toml'],
        
        # ==================== JAVASCRIPT/TYPESCRIPT ====================
        'jest': ['package.json'],
        'mocha': ['package.json'],
        'jasmine': ['package.json'],
        'vitest': ['package.json'],
        'ava': ['package.json'],
        'tap': ['package.json'],
        'karma': ['package.json', 'karma.conf.js'],
        'playwright': ['package.json'],
        'cypress': ['package.json', 'cypress.json', 'cypress.config.js', 'cypress.config.ts'],
        'puppeteer': ['package.json'],
        'nightwatch': ['package.json'],
        'protractor': ['package.json'],
        'webdriverio': ['package.json'],
        'testing-library': ['package.json'],
        'enzyme': ['package.json'],
        
        # ==================== RUBY ====================
        'rspec': ['Gemfile', 'Rakefile', '.rspec'],
        'minitest': ['Gemfile', 'Rakefile'],
        'testunit': ['Gemfile'],
        'cucumber-ruby': ['Gemfile', 'Rakefile'],
        'capybara': ['Gemfile'],
        'factory_bot': ['Gemfile'],
        
        # ==================== .NET / C# ====================
        'nunit': ['*.csproj', 'packages.config'],
        'xunit': ['*.csproj', 'packages.config'],
        'mstest': ['*.csproj', 'packages.config'],
        'specflow': ['*.csproj', 'packages.config'],
        'fluent-assertions': ['*.csproj', 'packages.config'],
        
        # ==================== GO ====================
        'go-test': ['go.mod', 'go.sum'],
        'testify': ['go.mod', 'go.sum'],
        'ginkgo': ['go.mod', 'go.sum'],
        'gomega': ['go.mod', 'go.sum'],
        'gocheck': ['go.mod', 'go.sum'],
        
        # ==================== RUST ====================
        'cargo-test': ['Cargo.toml'],
        'proptest': ['Cargo.toml'],
        'quickcheck': ['Cargo.toml'],
        
        # ==================== PHP ====================
        'phpunit': ['composer.json'],
        'pest': ['composer.json'],
        'codeception': ['composer.json', 'codeception.yml'],
        'behat': ['composer.json', 'behat.yml'],
        'phpspec': ['composer.json'],
        
        # ==================== SWIFT ====================
        'xctest': ['Package.swift', '*.xcodeproj'],
        'quick': ['Package.swift', 'Podfile'],
        'nimble': ['Package.swift', 'Podfile'],
        
        # ==================== KOTLIN ====================
        'kotest': ['build.gradle.kts', 'build.gradle'],
        'mockk': ['build.gradle.kts', 'build.gradle'],
        
        # ==================== SCALA ====================
        'scalatest': ['build.sbt'],
        'specs2': ['build.sbt'],
        'scalacheck': ['build.sbt'],
        
        # ==================== ELIXIR ====================
        'exunit': ['mix.exs'],
        'espec': ['mix.exs'],
        
        # ==================== C/C++ ====================
        'gtest': ['CMakeLists.txt', 'conanfile.txt', 'vcpkg.json'],
        'catch2': ['CMakeLists.txt', 'conanfile.txt', 'vcpkg.json'],
        'boost-test': ['CMakeLists.txt', 'conanfile.txt'],
        'ctest': ['CMakeLists.txt'],
        'doctest': ['CMakeLists.txt', 'conanfile.txt'],
        
        # ==================== DART/FLUTTER ====================
        'flutter-test': ['pubspec.yaml'],
        'dart-test': ['pubspec.yaml'],
        
        # ==================== ANDROID ====================
        'espresso': ['build.gradle', 'app/build.gradle'],
        'robolectric': ['build.gradle', 'app/build.gradle'],
    }
    
    framework_dependencies = {
        # ==================== JAVA ====================
        'junit': re.compile(r'junit|org\.junit'),
        'junit5': re.compile(r'junit-jupiter|org\.junit\.jupiter|junit-platform'),
        'testng': re.compile(r'testng|org\.testng'),
        'cucumber-java': re.compile(r'cucumber-java|cucumber-junit|io\.cucumber'),
        'spock': re.compile(r'spock-core|org\.spockframework'),
        'mockito': re.compile(r'mockito|org\.mockito'),
        'assertj': re.compile(r'assertj|org\.assertj'),
        
        # ==================== PYTHON ====================
        'pytest': re.compile(r'pytest'),
        'unittest': re.compile(r'unittest'),
        'nose': re.compile(r'\bnose\b(?!2)'),
        'nose2': re.compile(r'nose2'),
        'hypothesis': re.compile(r'hypothesis'),
        'behave': re.compile(r'behave'),
        'robot': re.compile(r'robotframework'),
        'tox': re.compile(r'\[tox\]|tox'),
        
        # ==================== JAVASCRIPT/TYPESCRIPT ====================
        'jest': re.compile(r'"jest"|\'jest\''),
        'mocha': re.compile(r'"mocha"|\'mocha\''),
        'jasmine': re.compile(r'"jasmine"|\'jasmine\''),
        'vitest': re.compile(r'"vitest"|\'vitest\''),
        'ava': re.compile(r'"ava"|\'ava\''),
        'tap': re.compile(r'"tap"|\'tap\'|"node-tap"'),
        'karma': re.compile(r'"karma"|\'karma\''),
        'playwright': re.compile(r'"@playwright/test"|"playwright"'),
        'cypress': re.compile(r'"cypress"|\'cypress\''),
        'puppeteer': re.compile(r'"puppeteer"|\'puppeteer\''),
        'nightwatch': re.compile(r'"nightwatch"|\'nightwatch\''),
        'protractor': re.compile(r'"protractor"|\'protractor\''),
        'webdriverio': re.compile(r'"webdriverio"|"@wdio/cli"'),
        'testing-library': re.compile(r'"@testing-library'),
        'enzyme': re.compile(r'"enzyme"|\'enzyme\''),
        
        # ==================== RUBY ====================
        'rspec': re.compile(r'rspec'),
        'minitest': re.compile(r'minitest'),
        'testunit': re.compile(r'test-unit'),
        'cucumber-ruby': re.compile(r'cucumber'),
        'capybara': re.compile(r'capybara'),
        'factory_bot': re.compile(r'factory_bot|factory_girl'),
        
        # ==================== .NET / C# ====================
        'nunit': re.compile(r'NUnit|nunit'),
        'xunit': re.compile(r'xunit|xUnit'),
        'mstest': re.compile(r'MSTest|Microsoft\.VisualStudio\.TestTools'),
        'specflow': re.compile(r'SpecFlow|specflow'),
        'fluent-assertions': re.compile(r'FluentAssertions'),
        
        # ==================== GO ====================
        'go-test': re.compile(r'testing'),
        'testify': re.compile(r'github\.com/stretchr/testify'),
        'ginkgo': re.compile(r'github\.com/onsi/ginkgo'),
        'gomega': re.compile(r'github\.com/onsi/gomega'),
        'gocheck': re.compile(r'gopkg\.in/check'),
        
        # ==================== RUST ====================
        'cargo-test': re.compile(r'\[dev-dependencies\]|\#\[test\]'),
        'proptest': re.compile(r'proptest'),
        'quickcheck': re.compile(r'quickcheck'),
        
        # ==================== PHP ====================
        'phpunit': re.compile(r'"phpunit/phpunit"'),
        'pest': re.compile(r'"pestphp/pest"'),
        'codeception': re.compile(r'"codeception/codeception"'),
        'behat': re.compile(r'"behat/behat"'),
        'phpspec': re.compile(r'"phpspec/phpspec"'),
        
        # ==================== SWIFT ====================
        'xctest': re.compile(r'XCTest|import\s+XCTest'),
        'quick': re.compile(r'Quick'),
        'nimble': re.compile(r'Nimble'),
        
        # ==================== KOTLIN ====================
        'kotest': re.compile(r'io\.kotest|kotest'),
        'mockk': re.compile(r'io\.mockk|mockk'),
        
        # ==================== SCALA ====================
        'scalatest': re.compile(r'scalatest|org\.scalatest'),
        'specs2': re.compile(r'specs2|org\.specs2'),
        'scalacheck': re.compile(r'scalacheck|org\.scalacheck'),
        
        # ==================== ELIXIR ====================
        'exunit': re.compile(r'ExUnit'),
        'espec': re.compile(r'espec'),
        
        # ==================== C/C++ ====================
        'gtest': re.compile(r'gtest|googletest|GTest'),
        'catch2': re.compile(r'catch2|Catch2'),
        'boost-test': re.compile(r'boost.*test|Boost.*Test'),
        'ctest': re.compile(r'enable_testing|add_test'),
        'doctest': re.compile(r'doctest'),
        
        # ==================== DART/FLUTTER ====================
        'flutter-test': re.compile(r'flutter_test'),
        'dart-test': re.compile(r'test:'),
        
        # ==================== ANDROID ====================
        'espresso': re.compile(r'espresso|androidx\.test\.espresso'),
        'robolectric': re.compile(r'robolectric'),
    }

    frameworks_found = []

    for framework, paths in test_framework_mapping.items():
        for path in paths:
            # Handle wildcard patterns
            if path.startswith('*.'):
                extension = path[1:]
                matching_files = [f for f in files if f.endswith(extension)]
                for matching_file in matching_files:
                    try:
                        content = get_file_content(owner, repo, matching_file, token)
                        if content and framework in framework_dependencies:
                            if framework_dependencies[framework].search(content):
                                if framework not in frameworks_found:
                                    frameworks_found.append(framework)
                    except Exception as e:
                        continue
            elif path in files:
                try:
                    content = get_file_content(owner, repo, path, token)
                    if content and framework in framework_dependencies:
                        if framework_dependencies[framework].search(content):
                            if framework not in frameworks_found:
                                frameworks_found.append(framework)
                except Exception as e:
                    continue

    return frameworks_found



def identify_test_frameworks_and_count_dependencies(files, owner, repo, token=None):
    """
    Identify test frameworks and count dependencies based on the presence of specific dependencies in build files.
    """
    test_frameworks = identify_test_frameworks(files, owner, repo, token)
    dependency_count = 0

    # Comprehensive list of dependency management files
    dependency_files = [
        # Java
        'pom.xml', 'build.gradle', 'build.gradle.kts',
        # Python
        'requirements.txt', 'requirements-dev.txt', 'requirements-test.txt',
        'pyproject.toml', 'Pipfile', 'setup.py', 'environment.yml', 'environment.yaml',
        # JavaScript/TypeScript
        'package.json',
        # Ruby
        'Gemfile',
        # PHP
        'composer.json',
        # Go
        'go.mod',
        # Rust
        'Cargo.toml',
        # Swift
        'Package.swift', 'Podfile', 'Cartfile',
        # Scala
        'build.sbt',
        # Elixir
        'mix.exs',
        # Dart/Flutter
        'pubspec.yaml',
        # Clojure
        'project.clj', 'deps.edn',
        # C/C++
        'vcpkg.json', 'conanfile.txt', 'conanfile.py', 'CMakeLists.txt',
        # Perl
        'cpanfile',
        # R
        'DESCRIPTION',
        # Julia
        'Project.toml',
        # .NET (special handling below for wildcards)
        'packages.config',
    ]
    
    # File extensions to check for .NET projects
    dotnet_extensions = ['.csproj', '.fsproj', '.vbproj']

    for file in files:
        # Check if the file is a recognized dependency file
        if file in dependency_files:
            try:
                content = get_file_content(owner, repo, file, token)
                dependency_count += count_dependencies(content, file)
            except Exception as e:
                print(f"Error fetching or counting dependencies in {file}: {e}")
                continue
        
        # Check for .NET project files
        for ext in dotnet_extensions:
            if file.endswith(ext):
                try:
                    content = get_file_content(owner, repo, file, token)
                    dependency_count += count_dependencies(content, file)
                except Exception as e:
                    print(f"Error fetching or counting dependencies in {file}: {e}")
                    continue
    
    return test_frameworks, dependency_count





# Identify the build language based on the presence of specific build files.
def identify_build_language(files):
    """
    Identify the build language based on the presence of specific build files.
    Returns the primary build system/language detected.
    """
    build_file_mapping = {
        # ==================== JAVA ====================
        'java-maven': ['pom.xml'],
        'java-gradle': ['build.gradle', 'settings.gradle', 'build.gradle.kts', 'gradlew'],
        'java-ant': ['build.xml'],
        
        # ==================== JAVASCRIPT/TYPESCRIPT ====================
        'nodejs-npm': ['package.json', 'package-lock.json'],
        'nodejs-yarn': ['yarn.lock'],
        'nodejs-pnpm': ['pnpm-lock.yaml'],
        'nodejs-bun': ['bun.lockb'],
        
        # ==================== PYTHON ====================
        'python-pip': ['requirements.txt', 'requirements-dev.txt'],
        'python-poetry': ['poetry.lock', 'pyproject.toml'],
        'python-pipenv': ['Pipfile', 'Pipfile.lock'],
        'python-setuptools': ['setup.py', 'setup.cfg'],
        'python-conda': ['environment.yml', 'environment.yaml', 'conda.yaml'],
        
        # ==================== RUBY ====================
        'ruby': ['Gemfile', 'Gemfile.lock', 'Rakefile'],
        'ruby-bundler': ['Gemfile.lock'],
        
        # ==================== .NET / C# ====================
        'dotnet': ['*.csproj', '*.fsproj', '*.vbproj', '*.sln', 'Directory.Build.props', 'global.json'],
        'dotnet-core': ['*.csproj', 'global.json'],
        'nuget': ['packages.config', 'nuget.config'],
        
        # ==================== GO ====================
        'go': ['go.mod', 'go.sum'],
        'go-dep': ['Gopkg.toml', 'Gopkg.lock'],
        
        # ==================== RUST ====================
        'rust-cargo': ['Cargo.toml', 'Cargo.lock'],
        
        # ==================== PHP ====================
        'php-composer': ['composer.json', 'composer.lock'],
        
        # ==================== SWIFT ====================
        'swift-spm': ['Package.swift', 'Package.resolved'],
        'swift-cocoapods': ['Podfile', 'Podfile.lock'],
        'swift-carthage': ['Cartfile', 'Cartfile.resolved'],
        
        # ==================== KOTLIN ====================
        'kotlin-gradle': ['build.gradle.kts', 'settings.gradle.kts'],
        
        # ==================== SCALA ====================
        'scala-sbt': ['build.sbt', 'project/build.properties'],
        'scala-mill': ['build.sc'],
        
        # ==================== ELIXIR ====================
        'elixir-mix': ['mix.exs', 'mix.lock'],
        
        # ==================== ERLANG ====================
        'erlang-rebar': ['rebar.config', 'rebar.lock'],
        
        # ==================== HASKELL ====================
        'haskell-cabal': ['*.cabal', 'cabal.project'],
        'haskell-stack': ['stack.yaml', 'stack.yaml.lock'],
        
        # ==================== CLOJURE ====================
        'clojure-lein': ['project.clj'],
        'clojure-deps': ['deps.edn'],
        
        # ==================== C/C++ ====================
        'cpp-cmake': ['CMakeLists.txt', 'cmake'],
        'cpp-make': ['Makefile', 'makefile', 'GNUmakefile'],
        'cpp-meson': ['meson.build'],
        'cpp-bazel': ['BUILD', 'WORKSPACE', 'BUILD.bazel', 'WORKSPACE.bazel'],
        'cpp-vcpkg': ['vcpkg.json'],
        'cpp-conan': ['conanfile.txt', 'conanfile.py'],
        
        # ==================== DART/FLUTTER ====================
        'dart-pub': ['pubspec.yaml', 'pubspec.lock'],
        'flutter': ['pubspec.yaml', 'flutter.yaml'],
        
        # ==================== ANDROID ====================
        'android-gradle': ['build.gradle', 'settings.gradle', 'gradlew', 'app/build.gradle'],
        
        # ==================== IOS ====================
        'ios-xcode': ['*.xcodeproj', '*.xcworkspace', 'Podfile'],
        
        # ==================== LUA ====================
        'lua-luarocks': ['*.rockspec'],
        
        # ==================== PERL ====================
        'perl-cpan': ['Makefile.PL', 'Build.PL', 'cpanfile'],
        
        # ==================== R ====================
        'r': ['DESCRIPTION', 'NAMESPACE', 'renv.lock'],
        
        # ==================== JULIA ====================
        'julia': ['Project.toml', 'Manifest.toml'],
        
        # ==================== TERRAFORM/IaC ====================
        'terraform': ['*.tf', 'terraform.tfvars', '.terraform.lock.hcl'],
        'pulumi': ['Pulumi.yaml', 'Pulumi.yml'],
        'ansible': ['ansible.cfg', 'playbook.yml', 'site.yml'],
        
        # ==================== DOCKER ====================
        'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore'],
        
        # ==================== KUBERNETES ====================
        'kubernetes': ['kustomization.yaml', 'Chart.yaml', 'values.yaml'],
        'helm': ['Chart.yaml', 'values.yaml'],
    }

    # Check for exact matches first
    for language, build_files in build_file_mapping.items():
        for build_file in build_files:
            if build_file.startswith('*.'):
                # Handle wildcard patterns
                extension = build_file[1:]  # Get the extension (e.g., '.csproj')
                if any(f.endswith(extension) for f in files):
                    return language
            elif build_file in files:
                return language
    
    return None







def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def parse_test_results(framework, log_content, build_language , framework_regex):
    """
    Parse the test results from the log content.
    """
    log_content = remove_ansi_escape_sequences(log_content)  # Remove ANSI escape codes
    if framework == "junit" and build_language == "java-maven":
        framework = "junit-maven"
    if framework == "junit" and build_language == "java-gradle":
        framework = "junit-gradle"

    if framework in framework_regex:
        #print("Framework: ", framework)
        #print("Build Language: ", build_language)

        # special case for junit-java and junit-maven
        if framework == "junit" and build_language == "java-maven":
            regex = framework_regex["junit-maven"]
            matches = regex.findall(log_content)
        elif framework == "junit" and build_language == "java-gradle":
            regex = framework_regex["junit-java"]
            matches = regex.findall(log_content)
        else:
            regex = framework_regex[framework]
            matches = regex.findall(log_content)

        # Debug statements
        # print("Log content: ", log_content)
        # print("Matches found: ", matches)

        if matches:
            passed_tests = 0
            failed_tests = 0
            skipped_tests = 0
            errors_tests = 0

            for match in matches:
                if framework == "pytest":
                    if match[0]:
                        passed_tests += int(match[0])
                    if match[1]:
                        failed_tests += int(match[1])
                    if match[2]:
                        skipped_tests += int(match[2])
                elif framework == "junit-gradle":
                    passed_tests += int(match[0])
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])  # Count errors for JUnit
                    skipped_tests += int(match[3])

                elif framework == "junit-maven":
                    passed_tests += int(match[0]) - int(match[1]) - int(match[2]) - int(
                        match[3])  # Subtract failed, errors, and skipped
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])  # Count errors for JUnit
                    skipped_tests += int(match[3])


                elif framework == "rspec":
                    if match[0]:
                        passed_tests += int(match[0])
                    if match[1]:
                        failed_tests += int(match[1])
                        passed_tests -= int(match[1])  # Subtract failed tests from passed
                    if match[2]:
                        skipped_tests += int(match[2])
                        passed_tests -= int(match[2])  # Subtract skipped tests from passed
                elif framework == "cucumber-ruby":
                    scenarios_skipped = int(match[1].split()[0]) if match[1] else 0
                    scenarios_undefined = int(match[2].split()[0]) if match[2] else 0
                    scenarios_failed = int(match[3].split()[0]) if match[3] else 0
                    scenarios_passed = int(match[4].split()[0]) if match[4] else 0
                    steps_skipped = int(match[6].split()[0]) if match[6] else 0
                    steps_undefined = int(match[7].split()[0]) if match[7] else 0
                    steps_failed = int(match[8].split()[0]) if match[8] else 0
                    steps_passed = int(match[9].split()[0]) if match[9] else 0

                    passed_tests += scenarios_passed + steps_passed
                    failed_tests += scenarios_failed + steps_failed
                    skipped_tests += scenarios_skipped + steps_skipped
                    # undefined_tests += scenarios_undefined + steps_undefined
                    # No skipped or errors for this format
                    # No errors for this format
                elif framework == "Cucumber-Java":
                    passed_tests += int(match[0])
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])
                    skipped_tests += int(match[3])
                elif framework == "testunit":
                    passed_tests += int(match[0])
                    # assertions += int(match[1])
                    failed_tests += int(match[2])
                    errors_tests += int(match[3])
                    # pendings, omissions, and notifications are not being counted in total

            total_tests = passed_tests + failed_tests + skipped_tests + errors_tests

            return {
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'total': total_tests
            }

    return {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}
