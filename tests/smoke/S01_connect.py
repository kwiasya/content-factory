"""S1: connect from .venv, read version and product name, open the smoke project."""

from _common import PROJECT, driver, run


def body(rec):
    d = driver()
    r = d.resolve
    rec["version_string"] = d.call(r.GetVersionString)
    rec["version"] = d.call(r.GetVersion)
    rec["product_name"] = d.call(r.GetProductName)
    rec["is_studio"] = d.call(r.IsStudio)
    rec["project"] = d.call(d.project.GetName)
    rec["page"] = d.call(r.GetCurrentPage)
    ok = rec["version_string"] and "Studio" in str(rec["product_name"]) and rec["project"] == PROJECT
    return "PASS" if ok else "FAIL"


run("S01_connect", body)
