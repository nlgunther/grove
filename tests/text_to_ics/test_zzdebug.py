import sys
def test_debug():
    print("SYS.PATH:", sys.path)
    import text_to_ics
    print("PATH:", text_to_ics.__path__)
