import copy
import struct
import unittest

from model_registry import NODE_ROLES, ACTION_ROLES, build_row, append_model, NORMAL_ID, bind_stats_row
from pkx_reference import ORDER
from sunny_park import stats_row


class ModelRegistryTests(unittest.TestCase):
    def scene(self):
        names = sorted({name for _, name in NODE_ROLES})
        return dict(object_name="SnivyExport",
                    nodes=[dict(name=name, index=i * 7) for i, name in enumerate(names)],
                    actions=[dict(name=name, index=i) for i, name in enumerate(ORDER)])

    def table(self):
        data = bytearray(48288)
        for offset, value in ((0, 670), (4, 72), (16, 48), (20, 670 * 72), (24, len(data))):
            struct.pack_into(">I", data, offset, value)
        for index in range(670):
            struct.pack_into(">II", data, 48 + index * 72 + 8, 0x10000000 + index, 0x20000000 + index)
            struct.pack_into(">H", data, 48 + index * 72 + 20, index % 494)
        return bytes(data)

    def test_resolves_roles_by_names_instead_of_foreign_indices(self):
        scene = self.scene()
        row = build_row(scene)
        nodes = {n["name"]: n["index"] for n in scene["nodes"]}
        actions = {n["name"]: n["index"] for n in scene["actions"]}
        self.assertEqual(list(row[25:50]), [nodes[name] for _, name in NODE_ROLES])
        self.assertEqual(list(row[50:72]), [actions[name] for _, name in ACTION_ROLES])
        self.assertNotEqual(row[25:50], bytes.fromhex("0f100d0e001922323a2a2512221000000000000f494a114b25"))

    def test_appends_without_changing_any_old_row(self):
        old = self.table()
        new = append_model(old, build_row(self.scene()))
        self.assertEqual(new[48:len(old)], old[48:])
        self.assertEqual(struct.unpack_from(">II", new), (671, 72))
        self.assertEqual(struct.unpack_from(">II", new, 20), (671 * 72, len(new)))
        with self.assertRaises(ValueError):
            append_model(new, build_row(self.scene()))

    def test_rejects_missing_anchor_ambiguous_and_overflowed_indices(self):
        original = self.scene()
        bad = copy.deepcopy(original)
        bad["nodes"] = [n for n in bad["nodes"] if n["name"] != "direct_set"]
        invalid = [bad]
        bad = copy.deepcopy(original)
        bad["nodes"][1]["index"] = bad["nodes"][0]["index"]
        invalid.append(bad)
        bad = copy.deepcopy(original)
        bad["nodes"][0]["index"] = 256
        invalid.append(bad)
        bad = copy.deepcopy(original)
        bad["actions"][0]["index"] = 1
        invalid.append(bad)
        for scene in invalid:
            with self.assertRaises(ValueError):
                build_row(scene)

    def test_rejects_id_collision_and_foreign_model_row(self):
        table = bytearray(self.table())
        struct.pack_into(">I", table, 48 + 8, NORMAL_ID)
        with self.assertRaises(ValueError):
            append_model(bytes(table), build_row(self.scene()))
        with self.assertRaises(ValueError):
            append_model(self.table(), bytes(72))

    def test_stats_binding_preserves_names_attributes_and_ability(self):
        old = stats_row(21775)
        new = bind_stats_row(old)
        self.assertEqual(new[:28], old[:28])
        self.assertEqual(new[30:], old[30:])
        self.assertEqual(struct.unpack_from(">H", new, 28)[0], 670)
        for row in (new, old[:-1]):
            with self.assertRaises(ValueError):
                bind_stats_row(row)


if __name__ == "__main__":
    unittest.main()
