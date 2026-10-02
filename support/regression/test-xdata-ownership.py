#!/usr/bin/env python3
"""Compile-time representation regression; requires no target execution."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def compile_case(compiler, root, text, flags):
    root.mkdir()
    (root / "input.c").write_text(text)
    subprocess.run([compiler, "-mmcs51", "--model-large", "--debug", *flags,
                    "-c", "input.c"], cwd=root, check=True, capture_output=True)
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
        assert one("interrupt_owner", "local")["owner_isr"]
        assert one("rent", "retained")["owner_reentrant"]
        assert one("rent", "retained")["class"] == "STATIC_LOCAL"
        assert not any(o["owner"] == "rent" and o["class"] != "STATIC_LOCAL" for o in objects)
        no_regs = compile_case(args.sdcc, root / "no-regs", source,
                               ["--no-reg-params", "--xdata-ownership"])
        rows = json.loads((no_regs / "input.xdata.json").read_bytes())["objects"]
        assert not any(o["class"] == "FIRST_ARGUMENT_HOME" for o in rows)
        assert any(o["owner"] == "foo" and o["symbol"] == "_foo_PARM_1" and
                   o["class"] == "PARAM_CALLER_WRITTEN" for o in rows)
        external = compile_case(args.sdcc, root / "extern",
                                "extern __xdata char missing; void f(void) { missing = 3; }\n",
                                ["--xdata-ownership"])
        rows = json.loads((external / "input.xdata.json").read_bytes())["objects"]
        assert not any(o["symbol"] == "_missing" for o in rows)
        assert b"S _missing Ref" in (external / "input.rel").read_bytes()
        for compiled in (control, off, on):
            subprocess.run([args.sdcc, "-mmcs51", "--model-large", "--debug",
                            "-o", "image.ihx", "input.rel"],
                           cwd=compiled, check=True, capture_output=True)
        for suffix in ("ihx", "cdb", "mem"):
            assert (control / ("image."+suffix)).read_bytes() == (on / ("image."+suffix)).read_bytes(), suffix
        print("XDATA ownership/classes, unchanged disabled/enabled artifacts and linked image PASS")


if __name__ == "__main__":
    main()
