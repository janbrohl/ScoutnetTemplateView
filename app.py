import re
from datetime import datetime, timedelta, date
from sn_rpc import get_data_by_global_id
from simpletal.simpleTALUtils import TemplateCache, TemplateRoot
from simpletal.simpleTALES import CachedFuncResult
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response
from vcapp import VCAppBase
from CommonMark import commonmark
from datetime import datetime, timedelta

TEMPLATE_PATH = "templates"

SAFE_NAME = re.compile("^[a-zA-Z][a-zA-Z0-9_]+$")

EPOCH = datetime(1970, 1, 1)


def from_timestamp(timestamp):
    return EPOCH + timedelta(seconds=timestamp)


class App(VCAppBase):

    def __init__(self, template_path):
        um = Map([Rule("/", endpoint="index", methods=("GET",)),
                  Rule("/<int:group_id>/", endpoint="group",
                       methods=("GET",), defaults={"template_name": "default"}),
                  Rule("/<int:group_id>/<template_name>",
                       endpoint="group", methods=("GET",))
                  ], strict_slashes=False)
        self.template_cache = TemplateCache()
        self.template_root = TemplateRoot(
            template_path, self.template_cache.getTemplate)
        VCAppBase.__init__(self, um)

    def view(self, endpoint, values, request, session, data):
        if endpoint == "group":
            group_id, group = data
            tn = values["template_name"]
            if SAFE_NAME.match(tn) is None:
                tn = "group_default"
            else:
                tn = "group_" + tn
            s = self.template_root.expand(
                tn, request.args, {"context": {"group": group,
                                               "events": CachedFuncResult(lambda: self.get_events(group, group_id)),
                                               "children": CachedFuncResult(lambda: self.get_children(group_id)),
                                               "parent": CachedFuncResult(lambda: self.get_group(group["IDX"][0]["parent_id"]))}})
        else:
            s = self.template_root.expand("index", request.args)
        return Response(s, mimetype="text/html")

    def ctrl(self, endpoint, values, request, session):
        if endpoint == "index":
            return None
        group_id = values["group_id"]
        group = self.get_group(group_id)
        return group_id, group

    def get_events(self, group, group_id):
        after = (date.today() - timedelta(days=30))
        data = get_data_by_global_id(
            group_id, {"events": {"after": after.isoformat()}})
        out = group.copy()
        for k, v in data.items():
            slot, _, _id = k.partition("_")
            out.setdefault(slot, []).append(v["content"])

        k_s = {}
        for s in out.get("STUFE", ()):
            k_s[s["Keywords_ID"]] = s
        for e in out["EVENT"]:

            sb = from_timestamp(float(e["Start"]))
            e["StartLocal"] = sb
            eb = from_timestamp(float(e["End"]))
            e["EndLocal"] = eb
            e["Stufen"] = [k_s[s] for s in e["Stufen"]]
            e["DescriptionMD"] = CachedFuncResult(
                lambda: commonmark(e["Description"] or ""))

        return out

    def get_group(self, group_id):
        data = get_data_by_global_id(
            group_id, {"kalenders": {}, "index": {}})
        out = {}
        for k, v in data.items():
            slot, _, _id = k.partition("_")
            vc = v["content"]
            if (slot == "IDX" and vc["url"] and not (vc["url"].startswith("https:") or vc["url"].startswith("http:"))):
                vc["url"] = "http://" + vc["url"]
            out.setdefault(slot, []).append(vc)

        return out

    def get_children(self, group_id):
        data = get_data_by_global_id(
            group_id, {"index": {"deeps": 1}})
        out = {}
        idx_group_id = "IDX_%i" % group_id
        for k, v in data.items():
            if not idx_group_id == k:
                slot, _, _id = k.partition("_")
                vc = v["content"]
                if (slot == "IDX" and vc["url"] and not (vc["url"].startswith("https:") or vc["url"].startswith("http:"))):
                    vc["url"] = "http://" + vc["url"]
                out.setdefault(slot, []).append(vc)
        return out


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = App(TEMPLATE_PATH)
    run_simple('127.0.0.1', 8080, app, use_debugger=True)
