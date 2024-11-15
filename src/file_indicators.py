def is_test_file(file_name):
    test_indicators = ['test', 'tests', 'spec', '__tests__', 'unittest', '/tests/', '/spec/']
    return any(indicator in file_name.lower() for indicator in test_indicators)


def is_production_file(file_path):
    # Expanded list of programming language extensions
    production_extensions = [
        '.py', '.java', '.cpp', '.js', '.ts', '.c', '.h', '.cs', '.swift', '.go',
        '.rb', '.php', '.kt', '.scala', '.groovy', '.rs', '.m', '.lua', '.pl',
        '.sh', '.bash', '.sql', '.ps1', '.cls', '.trigger', '.f', '.f90', '.asm',
        '.s', '.vhd', '.vhdl', '.verilog', '.sv', '.tml', '.json', '.xml', '.html',
        '.css', '.sass', '.less', '.jsp', '.asp', '.aspx', '.erb', '.twig', '.hbs'
    ]
    test_indicators = ['test', 'tests', 'spec', '__tests__']
    return (
            not any(indicator in file_path for indicator in test_indicators) and
            file_path.endswith(tuple(production_extensions))
    )