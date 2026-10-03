#!/usr/bin/env python3
"""Compile-time representation regression; requires no target execution."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{command!r}\n{result.stdout}\n{result.stderr}")
    return result


def compile_case(compiler, root, text, flags, debug=True):
    root.mkdir()
    (root / "input.c").write_text(text)
    run([compiler, "-mmcs51", "--model-large", *(["--debug"] if debug else []),
         *flags, "-c", "input.c"], root)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdcc", required=True)
    parser.add_argument("--control", required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name("xdata-ownership.c").read_text()
    with tempfile.TemporaryDirectory(prefix="sdcc-xdata-ownership-") as temporary:
        root = Path(temporary)
        control = compile_case(args.control, root / "control", source, [])
        off = compile_case(args.sdcc, root / "off", source, [])
        on = compile_case(args.sdcc, root / "on", source, ["--xdata-ownership"])
        assert not (off / "input.xdata.json").exists()
        for suffix in ("asm", "rel", "adb", "lst", "sym"):
            expected = (control / ("input."+suffix)).read_bytes()
            assert (off / ("input."+suffix)).read_bytes() == expected, ("off", suffix)
            assert (on / ("input."+suffix)).read_bytes() == expected, ("on", suffix)
        manifest = json.loads((on / "input.xdata.json").read_bytes())
        assert manifest["version"] == 1 and manifest["module"] == "input"
        objects = manifest["objects"]

        def one(owner, name):
            matches = [o for o in objects if o["owner"] == owner and o["name"] == name]
            assert len(matches) == 1, (owner, name, matches)
            return matches[0]

        assert one(None, "global")["class"] == "GLOBAL"
        assert one(None, "file_static")["class"] == "FILE_STATIC"
        assert one(None, "escaped")["class"] == "GLOBAL"
        assert one(None, "external")["class"] == "GLOBAL"
        for owner in ("foo", "bar"):
            assert one(owner, "local")["class"] == "LOCAL"
            assert one(owner, "first")["class"] == "FIRST_ARGUMENT_HOME"
        assert one("foo", "second")["class"] == "PARAM_CALLER_WRITTEN"
        assert one("foo", "second")["symbol"] == "_foo_PARM_2"
        assert one("foo", "retained")["class"] == "STATIC_LOCAL"
        assert one("foo", "array")["size"] == 3
        assert one("foo", "aggregate")["size"] == 3
        assert one("foo", "pointer")["size"] == 2
        assert one("foo", "first")["address_taken"]
        assert one("sibling", "local")["class"] == "LOCAL"
        assert one("interrupt_owner", "local")["owner_isr"]
        assert one("rent", "retained")["owner_reentrant"]
        assert one("rent", "retained")["class"] == "STATIC_LOCAL"
        assert not any(o["owner"] == "rent" and o["class"] != "STATIC_LOCAL" for o in objects)
        bank1 = compile_case(args.sdcc, root / "bank1", source,
                             ["--parms-in-bank1", "--xdata-ownership"])
        rows = json.loads((bank1 / "input.xdata.json").read_bytes())["objects"]
        assert any(o["owner"] == "foo" and o["name"] == "second" and
                   o["class"] == "REGISTER_ARGUMENT_HOME" for o in rows)
        bank1_control = compile_case(args.control, root / "bank1-control", source,
                                     ["--parms-in-bank1"])
        assert (bank1 / "input.rel").read_bytes() == (bank1_control / "input.rel").read_bytes()
        external = compile_case(args.sdcc, root / "extern",
                                "extern __xdata char missing; void f(void) { missing = 3; }\n",
                                ["--xdata-ownership"])
        rows = json.loads((external / "input.xdata.json").read_bytes())["objects"]
        assert not any(o["symbol"] == "_missing" for o in rows)
        assert b"S _missing Ref" in (external / "input.rel").read_bytes()
        for flags, debug in (([], False), (["--stack-auto"], True)):
            suffix = "debug-off" if not debug else "stack-auto"
            variant = source if not flags else (
                "__xdata volatile char global;\n"
                "char f(char a, char b) { volatile char local; static __xdata char retained;\n"
                "local = a + b; retained++; return local + retained; }\n"
                "void main(void) { global = f(1, 2); }\n")
            a = compile_case(args.control, root / (suffix+"-control"), variant, flags, debug)
            b = compile_case(args.sdcc, root / suffix, variant,
                             flags+["--xdata-ownership"], debug)
            for ext in ("asm", "rel", "lst", "sym"):
                assert (a / ("input."+ext)).read_bytes() == (b / ("input."+ext)).read_bytes()
            data = json.loads((b / "input.xdata.json").read_bytes())
            if flags:
                assert all(o["owner_reentrant"] and o["class"] == "STATIC_LOCAL"
                           for o in data["objects"] if o["owner"])
        special_source = (
            "__xdata unsigned char initialized = 7;\n"
            "__xdata __at(0x1234) unsigned char absolute;\n"
            "unsigned char * __xdata generic_pointer;\n"
            "void f(void) { extern __xdata unsigned char outside; outside = initialized; }\n")
        a = compile_case(args.control, root / "special-control", special_source, [])
        b = compile_case(args.sdcc, root / "special", special_source, ["--xdata-ownership"])
        assert (a / "input.rel").read_bytes() == (b / "input.rel").read_bytes()
        data = {o["name"]: o for o in json.loads((b / "input.xdata.json").read_bytes())["objects"]}
        assert data["initialized"]["area"] == "XISEG"
        assert data["absolute"]["absolute"] and data["absolute"]["address"] == 0x1234
        assert data["generic_pointer"]["size"] == 3
        assert all(o["owner"] is None for o in data.values())
        assert "outside" not in data
        assert b"S _outside Ref" in (b / "input.rel").read_bytes()
        inline_source = (
            "extern void consume(unsigned char *p);\n"
            "static inline unsigned char callee(unsigned char arg) {\n"
            "if (arg == 1) return 3; consume(&arg); if (arg == 2) return 4; return arg; }\n"
            "unsigned char caller(unsigned char arg) {\n"
            "return callee(arg) + callee(arg + 1); }\n")
        a = compile_case(args.control, root / "inline-control", inline_source, ["--std-c99"])
        b = compile_case(args.sdcc, root / "inline", inline_source, ["--std-c99", "--xdata-ownership"])
        assert (a / "input.rel").read_bytes() == (b / "input.rel").read_bytes()
        rows = json.loads((b / "input.xdata.json").read_bytes())["objects"]
        assert any(o["class"] == "INLINE_RETURN_HOME" for o in rows), rows
        assert all(o["owner"] in ("callee", "caller") for o in rows)
        rmw_source = (
            "extern unsigned char *advance(void);\n"
            "extern unsigned char fetched(void);\n"
            "void rmw(void) { (*advance()) += fetched(); }\n")
        a = compile_case(args.control, root / "rmw-control", rmw_source, [])
        b = compile_case(args.sdcc, root / "rmw", rmw_source, ["--xdata-ownership"])
        assert (a / "input.rel").read_bytes() == (b / "input.rel").read_bytes()
        rows = json.loads((b / "input.xdata.json").read_bytes())["objects"]
        assert not rows, "This fixture keeps its AST temporary out of static XDATA"
        retained_rmw = rmw_source.replace("*advance", "* volatile advance", 1)
        a = compile_case(args.control, root / "retained-rmw-control", retained_rmw, [])
        off_rmw = compile_case(args.sdcc, root / "retained-rmw-off", retained_rmw, [])
        b = compile_case(args.sdcc, root / "retained-rmw", retained_rmw, ["--xdata-ownership"])
        for suffix in ("asm", "rel", "adb", "lst", "sym"):
            assert (a / ("input." + suffix)).read_bytes() == (b / ("input." + suffix)).read_bytes()
            assert (a / ("input." + suffix)).read_bytes() == (off_rmw / ("input." + suffix)).read_bytes()
        rows = json.loads((b / "input.xdata.json").read_bytes())["objects"]
        assert len(rows) == 1 and rows[0]["class"] == "COMPILER_TEMP", rows
        row = rows[0]
        assert row["owner"] == "rmw" and row["owner_symbol"] == "_rmw"
        assert row["area"] == "XSEG" and row["size"] == 3 and not row["absolute"]
        assert row["symbol"] + ":" in (b / "input.asm").read_text()
        assert row["cdb_key"] in (b / "input.adb").read_text()
        blocked = root / "blocked"
        blocked.mkdir()
        (blocked / "input.c").write_text(source)
        (blocked / "input.xdata.json").mkdir()
        failed = subprocess.run([args.sdcc, "-mmcs51", "--model-large",
                                 "--xdata-ownership", "-c", "input.c"],
                                cwd=blocked, text=True, capture_output=True)
        assert failed.returncode and "input.xdata.json" in failed.stderr
        for compiler, compiled in ((args.control, control), (args.sdcc, off), (args.sdcc, on)):
            run([compiler, "-mmcs51", "--model-large", "--debug",
                 "-o", "image.ihx", "input.rel"], compiled)
        for suffix in ("ihx", "cdb", "mem"):
            for compiled in (off, on):
                assert (control / ("image."+suffix)).read_bytes() == (compiled / ("image."+suffix)).read_bytes(), suffix
        print("XDATA ownership/classes, unchanged disabled/enabled artifacts and linked image PASS")


if __name__ == "__main__":
    main()
