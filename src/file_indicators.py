def is_test_file(file_name):
    """
    Detect if a file is a test file based on common naming conventions.
    """
    file_lower = file_name.lower()
    
    # Directory-based indicators (strongest signal)
    test_directories = [
        '/test/', '/tests/', '/spec/', '/specs/',
        '/__tests__/', '/__test__/',
        '/testing/', '/unittest/', '/unittests/',
        '/integration/', '/e2e/', '/functional/',
        '/fixtures/', '/mocks/', '/stubs/',
        '/test_', '/tests_',
        'test/', 'tests/', 'spec/', 'specs/',
    ]
    
    # File name patterns
    test_file_patterns = [
        # Python: test_*.py, *_test.py
        'test_', '_test.py', '_tests.py',
        # Go: *_test.go
        '_test.go',
        # Java/JUnit: *Test.java, Test*.java, *Tests.java
        'test.java', 'tests.java',
        # JavaScript/TypeScript: *.test.js, *.spec.js, *.test.ts, *.spec.ts
        '.test.js', '.test.ts', '.test.jsx', '.test.tsx',
        '.spec.js', '.spec.ts', '.spec.jsx', '.spec.tsx',
        # Ruby: *_spec.rb, *_test.rb
        '_spec.rb', '_test.rb',
        # PHP: *Test.php
        'test.php',
        # Rust: tests.rs (usually in tests/ directory)
        # C#: *Tests.cs, *Test.cs
        'test.cs', 'tests.cs',
        # Swift: *Tests.swift
        'tests.swift',
        # Kotlin: *Test.kt
        'test.kt',
    ]
    
    # Check directory patterns
    if any(indicator in file_lower for indicator in test_directories):
        return True
    
    # Check file name patterns
    if any(file_lower.endswith(pattern) or pattern in file_lower for pattern in test_file_patterns):
        return True
    
    # Legacy indicators (for backward compatibility)
    legacy_indicators = ['__tests__', 'unittest']
    if any(indicator in file_lower for indicator in legacy_indicators):
        return True
    
    return False


def is_production_file(file_path):
    """
    Detect if a file is a production source code file.
    Excludes test files and non-code files.
    """
    # Comprehensive list of programming language extensions
    production_extensions = [
        # ==================== POPULAR LANGUAGES ====================
        # Python
        '.py', '.pyw', '.pyx', '.pxd', '.pxi',
        # JavaScript/TypeScript
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.mts', '.cts',
        # Java
        '.java',
        # C/C++
        '.c', '.h', '.cpp', '.hpp', '.cc', '.hh', '.cxx', '.hxx', '.c++', '.h++',
        '.ino',  # Arduino
        # C#
        '.cs', '.csx',
        # Go
        '.go',
        # Rust
        '.rs',
        # Ruby
        '.rb', '.rake', '.gemspec',
        # PHP
        '.php', '.phtml', '.php3', '.php4', '.php5', '.php7', '.phps',
        # Swift
        '.swift',
        # Kotlin
        '.kt', '.kts',
        # Scala
        '.scala', '.sc',
        # Groovy
        '.groovy', '.gvy', '.gy', '.gsh',
        
        # ==================== SYSTEMS PROGRAMMING ====================
        # Assembly
        '.asm', '.s', '.S',
        # Objective-C
        '.m', '.mm',
        # D
        '.d',
        # Zig
        '.zig',
        # Nim
        '.nim', '.nims',
        # V
        '.v',
        # Crystal
        '.cr',
        # Haxe
        '.hx',
        
        # ==================== FUNCTIONAL LANGUAGES ====================
        # Haskell
        '.hs', '.lhs',
        # Elixir
        '.ex', '.exs',
        # Erlang
        '.erl', '.hrl',
        # Clojure
        '.clj', '.cljs', '.cljc', '.edn',
        # F#
        '.fs', '.fsi', '.fsx', '.fsscript',
        # OCaml
        '.ml', '.mli',
        # Elm
        '.elm',
        # PureScript
        '.purs',
        # Racket/Scheme/Lisp
        '.rkt', '.scm', '.ss', '.lisp', '.lsp', '.cl',
        
        # ==================== SCRIPTING LANGUAGES ====================
        # Lua
        '.lua',
        # Perl
        '.pl', '.pm', '.t', '.pod',
        # Shell
        '.sh', '.bash', '.zsh', '.fish', '.ksh', '.csh', '.tcsh',
        # PowerShell
        '.ps1', '.psm1', '.psd1',
        # Tcl
        '.tcl',
        # AWK
        '.awk',
        
        # ==================== DATA SCIENCE ====================
        # R
        '.r', '.R', '.rmd', '.Rmd',
        # Julia
        '.jl',
        # MATLAB/Octave
        '.m', '.mat',
        # SAS
        '.sas',
        # Stata
        '.do', '.ado',
        
        # ==================== DATABASE ====================
        # SQL
        '.sql', '.psql', '.plsql', '.plpgsql',
        # Salesforce
        '.cls', '.trigger', '.apex',
        
        # ==================== WEB/FRONTEND ====================
        # HTML
        '.html', '.htm', '.xhtml',
        # CSS
        '.css', '.scss', '.sass', '.less', '.styl', '.stylus',
        # Vue
        '.vue',
        # Svelte
        '.svelte',
        # Angular templates
        '.component.ts', '.component.html',
        # JSP/ASP
        '.jsp', '.asp', '.aspx', '.ascx',
        # Template engines
        '.erb', '.ejs', '.hbs', '.handlebars', '.mustache', '.pug', '.jade',
        '.jinja', '.jinja2', '.twig', '.blade.php', '.liquid',
        # WebAssembly
        '.wat', '.wasm',
        
        # ==================== MOBILE ====================
        # Dart/Flutter
        '.dart',
        # React Native (uses .js/.tsx)
        # Android XML layouts
        '.xml',  # Note: also used elsewhere
        
        # ==================== CONFIG AS CODE ====================
        # Terraform
        '.tf', '.tfvars',
        # HCL
        '.hcl',
        # Pulumi
        # Uses standard language files
        # Ansible
        '.yml', '.yaml',  # Note: also used elsewhere
        # CloudFormation
        # Uses .yml/.json
        
        # ==================== SMART CONTRACTS ====================
        # Solidity
        '.sol',
        # Vyper
        '.vy',
        # Move
        '.move',
        # Cairo
        '.cairo',
        
        # ==================== HARDWARE ====================
        # VHDL
        '.vhd', '.vhdl',
        # Verilog/SystemVerilog
        '.v', '.sv', '.svh',
        # Chisel (uses .scala)
        
        # ==================== OTHER ====================
        # Fortran
        '.f', '.f90', '.f95', '.f03', '.f08', '.for',
        # COBOL
        '.cob', '.cbl', '.cpy',
        # Pascal/Delphi
        '.pas', '.pp', '.dpr',
        # Ada
        '.adb', '.ads',
        # Prolog
        '.pl', '.pro',
        # ABAP
        '.abap',
        # LabVIEW
        '.vi',
        # GraphQL
        '.graphql', '.gql',
        # Protocol Buffers
        '.proto',
        # Thrift
        '.thrift',
        # Cap'n Proto
        '.capnp',
        # JSON (sometimes code)
        '.json',
        # TOML
        '.toml',
    ]
    
    # Test indicators to exclude
    test_indicators = [
        'test', 'tests', 'spec', 'specs',
        '__tests__', '__test__',
        '_test.', '_tests.', '_spec.', '_specs.',
        '.test.', '.tests.', '.spec.', '.specs.',
        '/test/', '/tests/', '/spec/', '/specs/',
        '/fixtures/', '/mocks/', '/stubs/',
        '/e2e/', '/integration/', '/functional/',
    ]
    
    file_lower = file_path.lower()
    
    # Check if it's a test file
    if any(indicator in file_lower for indicator in test_indicators):
        return False
    
    # Check if it has a production extension
    return file_path.endswith(tuple(production_extensions))