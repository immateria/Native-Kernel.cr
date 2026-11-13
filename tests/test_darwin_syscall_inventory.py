"""Contracts for the tracked Darwin syscall inventory."""
import ast
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/catalog/darwin_syscall_inventory.py"
SPEC = importlib.util.spec_from_file_location("darwin_syscall_inventory", SCRIPT)
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_fake_exact_tree(root, definitions=None):
    definitions = definitions or {
        "osfmk/mach/task.defs": "subsystem task 3400;\nroutine ping();\n",
    }
    for relative in inventory.DIRECT_SOURCE_ROLES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "libsyscall/xcodescripts/mach_install_mig.sh":
            content = 'MIGS=""\nMIGS_INTERNAL=""\n'
        else:
            content = "fixture for %s\n" % relative
        path.write_text(content, encoding="utf-8")
    for relative, content in definitions.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    paths = set(inventory.DIRECT_SOURCE_ROLES)
    paths.update(definitions)
    files = []
    for relative in sorted(paths):
        path = root / relative
        content = path.read_text(encoding="utf-8")
        files.append({
            "path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "role": inventory.manifest_role(relative, content),
        })
    document = {
        "schema_version": 1,
        "snapshot_id": inventory.EXACT_SNAPSHOT,
        "source_repository": inventory.SOURCE_REPOSITORY,
        "commit": inventory.EXACT_COMMIT,
        "files": files,
    }
    manifest = root.parent / "manifest.json"
    manifest.write_bytes(inventory.source_manifest_bytes(document))
    return manifest, document


def write_mig_controls(root):
    makefile = root / "osfmk/mach/Makefile"
    makefile.parent.mkdir(parents=True, exist_ok=True)
    makefile.write_text("MIG_DEFS = task.defs\\\n\n", encoding="utf-8")
    script = root / "libsyscall/xcodescripts/mach_install_mig.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text('MIGS="task.defs"\nMIGS_INTERNAL="task.defs"\n',
                      encoding="utf-8")


class DarwinSyscallInventory(unittest.TestCase):
    def setUp(self):
        metadata_path = ROOT / "docs/data/darwin-syscall-inventory.json"
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        snapshot = self.metadata["snapshot_id"]
        self.active = read_csv(ROOT / "docs/data" / ("darwin-active-syscalls-%s.csv" % snapshot))
        self.gaps = read_csv(ROOT / "docs/data" / ("darwin-syscall-gaps-%s.csv" % snapshot))
        self.secondary = read_csv(
            ROOT / "docs/data" / ("darwin-secondary-catalog-candidates-%s.csv" % snapshot)
        )
        self.proc_info = read_csv(
            ROOT / "docs/data" / ("darwin-proc-info-operations-%s.csv" % snapshot)
        )
        self.mig_subsystems = read_csv(
            ROOT / "docs/data" / ("darwin-mach-mig-subsystems-%s.csv" % snapshot)
        )

    def test_tracked_counts_and_complement(self):
        self.assertEqual(len(self.active), self.metadata["active_logical_rows"])
        self.assertEqual(len(self.gaps), self.metadata["gap_rows"])
        implemented = [row for row in self.active
                       if row["native_kernel_state"] == "typed_wrapper"]
        expected_gaps = [row for row in self.active
                         if row["native_kernel_state"] != "typed_wrapper"]
        self.assertEqual(len(implemented), self.metadata["typed_wrapper_rows"])
        self.assertEqual(self.gaps, expected_gaps)
        self.assertEqual(sum(bool(row["parse_warning"]) for row in self.active),
                         self.metadata["active_parse_warning_rows"])
        self.assertEqual(len(self.secondary), self.metadata["secondary_catalog_candidate_rows"])

    def test_pinned_latest_snapshot_counts(self):
        self.assertEqual(self.metadata["snapshot_id"], "xnu-12377.121.6")
        self.assertEqual(self.metadata["schema_version"], 5)
        self.assertEqual(self.metadata["history_snapshot_rows_all_statuses"], 843)
        self.assertEqual(self.metadata["corrected_snapshot_rows_all_statuses"], 845)
        correction = self.metadata["exact_source_correction"]
        self.assertEqual(correction["commit"], inventory.EXACT_COMMIT)
        self.assertEqual(correction["history_export_input_commit"],
                         inventory.HISTORY_LATEST_INPUT_COMMIT)
        self.assertTrue(correction["history_export_label_mismatch"])
        self.assertEqual(len(self.active), 533)
        self.assertEqual(len(self.gaps), 489)
        self.assertEqual(self.metadata["typed_wrapper_rows"], 44)
        self.assertEqual(self.metadata["active_parse_warning_rows"], 2)
        self.assertEqual(len(self.secondary), 218)
        self.assertEqual(len(self.proc_info), 94)
        self.assertEqual(self.metadata["proc_info_implemented_rows"], 14)
        self.assertEqual(len(self.mig_subsystems), 52)
        self.assertEqual(self.metadata["mig_production_subsystem_rows"], 49)
        self.assertEqual(self.metadata["mig_kernel_build_subsystem_rows"], 37)
        self.assertEqual(self.metadata["mig_libsyscall_export_subsystem_rows"], 17)
        manifest = correction["source_manifest"]
        self.assertEqual(manifest["file_count"], 99)
        self.assertEqual(manifest["defs_file_count"], 85)
        self.assertEqual(manifest["sha256"], inventory.sha256(inventory.SOURCE_MANIFEST))

    def test_proc_info_call_catalog_is_contiguous(self):
        calls = [row for row in self.proc_info if row["category"] == "call"]
        self.assertEqual([int(row["numeric_value"]) for row in calls],
                         list(range(1, 21)))
        states = {row["symbol"]: row["native_kernel_state"] for row in calls}
        self.assertEqual(states["PROC_INFO_CALL_LISTPIDS"], "implemented")
        self.assertEqual(states["PROC_INFO_CALL_PIDINFO"], "implemented")
        self.assertEqual(states["PROC_INFO_CALL_PIDRUSAGE"], "implemented")
        self.assertEqual(states["PROC_INFO_CALL_SIGNAL_AUDITTOKEN"], "implemented")
        self.assertEqual(states["PROC_INFO_CALL_TERMINATE"], "unreviewed")

    def test_proc_info_implementation_marks_have_witnesses(self):
        self.assertEqual(set(inventory.IMPLEMENTED_PROC_INFO),
                         set(inventory.PROC_INFO_WITNESSES))
        for symbol, (relative, marker) in inventory.PROC_INFO_WITNESSES.items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), "%s witness for %s" % (relative, symbol))
            self.assertIn(marker, path.read_text(encoding="utf-8"), symbol)
        states = {row["symbol"]: row["native_kernel_state"] for row in self.proc_info}
        self.assertEqual(sum(state == "implemented" for state in states.values()), 14)
        self.assertEqual(states["PROC_PIDT_SHORTBSDINFO"], "implemented")
        self.assertEqual(states["PROC_PIDT_BSDINFOWITHUNIQID"], "implemented")
        self.assertEqual(states["PROC_PIDUNIQIDENTIFIERINFO"], "unreviewed")

    def test_mig_map_separates_tests_from_production_sources(self):
        test_rows = [row for row in self.mig_subsystems
                     if row["source_scope"] == "test_only"]
        production_rows = [row for row in self.mig_subsystems
                           if row["source_scope"] != "test_only"]
        self.assertEqual(len(test_rows), 3)
        self.assertEqual(len(production_rows), 49)
        by_names = {row["subsystem_names"]: row for row in production_rows}
        self.assertEqual(by_names["task"]["base_message_id"], "3400")
        self.assertEqual(by_names["thread_act"]["base_message_id"], "3600")
        self.assertEqual(by_names["mach_port"]["base_message_id"], "3200")
        self.assertIn("kernel_public", by_names["task"]["kernel_build_roles"])
        self.assertIn("public_header", by_names["task"]["libsyscall_export_roles"])
        self.assertIn("public_header_macos",
                      by_names["mach_vm;vm_map_lp64_local"]["libsyscall_export_roles"])

    def test_diagnostic_rows_use_exact_implementation_receipts(self):
        diagnostics = [row for row in self.active if row["family"] == "diagnostic"]
        self.assertEqual(len(diagnostics), 5)
        by_name = {row["logical_name"]: row for row in diagnostics}
        exact_hash = inventory.EXACT_SOURCE_SHA256["osfmk/i386/Diagnostics.c"]
        for row in diagnostics:
            self.assertEqual(row["implementation_source_path"],
                             "osfmk/i386/Diagnostics.c")
            self.assertEqual(row["implementation_source_hash"], exact_hash)
            self.assertTrue(row["implementation_source_line"])
            self.assertNotIn("68c4cab00fed224432e0e350e29fe4eea", str(row.values()))
        self.assertEqual(by_name["dgGzallocTest"]["condition"],
                         "DEVELOPMENT || DEBUG")
        self.assertEqual(by_name["dgPermCheck"]["condition"],
                         "DEVELOPMENT || DEBUG")
        self.assertEqual(by_name["dgEnaPMC"]["condition"], "1")

    def test_mach_slot_63_uses_exact_tag_signature(self):
        rows = [row for row in self.active
                if row["family"] == "mach" and row["number"] == "63"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["condition"], "__LP64__")
        self.assertEqual(row["arg_count"], "3")
        self.assertEqual(row["arg_words"], "5")
        self.assertEqual(row["munger"], "munge_wll")
        self.assertEqual(
            row["source_hash"],
            inventory.EXACT_SOURCE_SHA256["osfmk/kern/syscall_sw.c"],
        )

    def test_secondary_queue_names_known_multiplexers(self):
        by_name = {row["logical_name"]: row for row in self.secondary}
        self.assertEqual(by_name["ioctl"]["selector_parameters"], "com")
        self.assertEqual(by_name["proc_info"]["selector_parameters"], "callnum;flavor")
        self.assertEqual(by_name["process_policy"]["selector_parameters"],
                         "scope;action;policy;policy_subtype")
        self.assertEqual(by_name["mmap"]["selector_parameters"], "prot;flags")

    def test_implemented_rows_match_numeric_raw_calls(self):
        discovered = set(inventory.discover_raw_coverage(ROOT))
        tracked = {(row["family"], int(row["number"])) for row in self.active
                   if row["native_kernel_state"] == "typed_wrapper"}
        self.assertEqual(tracked, discovered)

    def test_generator_preserves_logical_variants(self):
        fields = list(inventory.SOURCE_COLUMNS)
        rows = [
            dict.fromkeys(fields, ""),
            dict.fromkeys(fields, ""),
            dict.fromkeys(fields, ""),
        ]
        rows[0].update({"snapshot_id": "xnu-1.0.0", "family": "bsd", "architecture": "all",
                        "number": "20", "logical_name": "getpid", "handler": "getpid",
                        "status": "active", "source_path": "bsd/kern/syscalls.master",
                        "source_line": "1"})
        rows[1].update({"snapshot_id": "xnu-1.0.0", "family": "diagnostic",
                        "architecture": "x86_64", "number": "7",
                        "logical_name": "first", "handler": "first", "status": "active",
                        "source_path": "osfmk/i386/Diagnostics.h", "source_line": "2"})
        rows[2].update({"snapshot_id": "xnu-1.0.0", "family": "diagnostic",
                        "architecture": "x86_64", "number": "7",
                        "logical_name": "second", "handler": "second", "status": "active",
                        "source_path": "osfmk/i386/Diagnostics.h", "source_line": "3"})
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/native-kernel/darwin/process.cr"
            source.parent.mkdir(parents=True)
            source.write_text("Raw.call(20)\n", encoding="utf-8")
            archive = root / "history.zip"
            member = "bundle/output/latest_snapshot_entries.csv"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(member, output.getvalue())
            generated = inventory.build_outputs(archive, root)

        active = next(value for name, value in generated.items()
                      if name.startswith("darwin-active-syscalls-"))
        decoded = list(csv.DictReader(io.StringIO(active.decode("utf-8"))))
        self.assertEqual([row["logical_name"] for row in decoded],
                         ["getpid", "first", "second"])
        self.assertEqual(decoded[0]["native_kernel_state"], "typed_wrapper")
        self.assertEqual(decoded[1]["native_kernel_state"], "unsupported_entry_family")
        self.assertEqual(decoded[2]["native_kernel_state"], "unsupported_entry_family")

    def test_discovery_resolves_planned_symbolic_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            darwin = root / "src/native-kernel/darwin"
            darwin.mkdir(parents=True)
            (darwin / "raw.cr").write_text(
                "module Native::Kernel::Darwin::Syscall::Number\n"
                "  GETPID = 20_i32\n"
                "end\n",
                encoding="utf-8",
            )
            (darwin / "mach.cr").write_text(
                "module Native::Kernel::Darwin::Mach::Trap\n"
                "  TASK_SELF = -28_i32\n"
                "end\n"
                "Raw.call(Mach::Trap::TASK_SELF)\n",
                encoding="utf-8",
            )
            (darwin / "process.cr").write_text(
                "Raw.call(Syscall::Number::GETPID)\n",
                encoding="utf-8",
            )
            coverage = inventory.discover_raw_coverage(root)

        self.assertEqual(set(coverage), {("bsd", 20), ("mach", 28)})
        self.assertEqual(coverage[("bsd", 20)]["forms"], {"symbolic"})
        self.assertEqual(coverage[("mach", 28)]["forms"], {"symbolic"})

    def test_discovery_rejects_ambiguous_numeric_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            darwin = root / "src/native-kernel/darwin"
            darwin.mkdir(parents=True)
            (darwin / "raw.cr").write_text(
                "X = 1_i32\nX = 2_i32\nRaw.call(Syscall::Number::X)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(inventory.CatalogError, "uniquely"):
                inventory.discover_raw_coverage(root)

    def test_exact_snapshot_requires_exact_xnu_source(self):
        fields = list(inventory.SOURCE_COLUMNS)
        row = dict.fromkeys(fields, "")
        row.update({
            "snapshot_id": inventory.EXACT_SNAPSHOT,
            "family": "bsd",
            "architecture": "all",
            "number": "20",
            "logical_name": "getpid",
            "handler": "getpid",
            "status": "active",
        })
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/native-kernel/darwin/process.cr"
            source.parent.mkdir(parents=True)
            source.write_text("Raw.call(20)\n", encoding="utf-8")
            archive = root / "history.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("bundle/output/latest_snapshot_entries.csv",
                                output.getvalue())
            with self.assertRaisesRegex(inventory.CatalogError,
                                        "requires --latest-xnu-root"):
                inventory.build_outputs(archive, root)

    def test_exact_mach_parser_preserves_conditional_variants(self):
        rows = inventory.parse_exact_mach(
            "#if __LP64__\n"
            "/* 63 */ MACH_TRAP(foo, 3, 5, munge_wll),\n"
            "#else\n"
            "/* 63 */ MACH_TRAP(kern_invalid, 0, 0, NULL),\n"
            "#endif\n",
            "source-hash",
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["condition"], "__LP64__")
        self.assertEqual(rows[0]["arg_count"], "3")
        self.assertEqual(rows[0]["arg_words"], "5")
        self.assertEqual(rows[0]["munger"], "munge_wll")
        self.assertEqual(rows[1]["condition"], "!(__LP64__)")
        self.assertEqual(rows[1]["status"], "inactive")

    def test_exact_mach_parser_accepts_multiline_rows_and_rejects_bad_conditions(self):
        rows = inventory.parse_exact_mach(
            "#if FEATURE\n"
            "/* 7 */ MACH_TRAP(\n"
            "  useful_trap,\n"
            "  2, 3, munge_w),\n"
            "#endif\n",
            "hash",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["handler"], "useful_trap")
        self.assertEqual(rows[0]["condition"], "FEATURE")
        with self.assertRaisesRegex(inventory.CatalogError, "Unterminated"):
            inventory.parse_exact_mach(
                "#if FEATURE\n/* 7 */ MACH_TRAP(useful_trap, 0),\n", "hash"
            )
        with self.assertRaisesRegex(inventory.CatalogError, "Duplicate.*#else"):
            inventory.parse_exact_mach(
                "#if FEATURE\n#else\n#else\n#endif\n", "hash"
            )

    def test_arm_parser_is_scoped_to_platform_dispatcher(self):
        header = "#define PLATFORM_SYSCALL_TRAP_NO 0x80000000\n"
        implementation = (
            "void unrelated(void) { switch (x) { case 99: break; } }\n"
            "void platform_syscall(void *state) {\n"
            "  switch (code) {\n"
            "  case 2: thread_set_cthread_self(0); break;\n"
            "  case 0: /* removed */ break;\n"
            "  default: break;\n"
            "  }\n"
            "}\n"
        )
        rows = inventory.parse_exact_arm_platform(header, implementation, "h", "i")
        self.assertEqual([row["selector"] for row in rows], ["2", "0"])

    def test_diagnostic_parser_preserves_conditions_and_declared_only_rows(self):
        header = (
            "#define diagSCnum 0x6000\n"
            "#define dgAlways 1\n"
            "#define dgDebug 2\n"
            "#define dgNested 3\n"
            "#define dgDeclared 4\n"
        )
        implementation = (
            "int diagCall64(void *state) {\n"
            "  switch (selector) {\n"
            "  case dgAlways: break;\n"
            "#if DEVELOPMENT || DEBUG\n"
            "  case dgDebug: break;\n"
            "#if EXTRA\n"
            "  case dgNested: break;\n"
            "#endif\n"
            "#endif\n"
            "  default: break;\n"
            "  }\n"
            "}\n"
        )
        rows = inventory.parse_exact_diagnostics(header, implementation, "hh", "ih")
        by_name = {row["logical_name"]: row for row in rows}
        self.assertEqual(by_name["dgAlways"]["condition"], "1")
        self.assertEqual(by_name["dgDebug"]["condition"], "DEVELOPMENT || DEBUG")
        self.assertEqual(by_name["dgNested"]["condition"],
                         "(DEVELOPMENT || DEBUG) && (EXTRA)")
        self.assertEqual(by_name["dgDeclared"]["status"], "declared_only")
        self.assertEqual(by_name["dgDeclared"]["implementation_source_hash"], "")
        with self.assertRaisesRegex(inventory.CatalogError, "Duplicate"):
            inventory.parse_exact_diagnostics(
                header,
                implementation.replace("case dgAlways: break;",
                                       "case dgAlways: break;\ncase dgAlways: break;"),
                "hh", "ih",
            )

    def test_mig_parser_records_keyword_line_and_source_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_mig_controls(root)
            source = root / "osfmk/mach/task.defs"
            source.write_text(
                "\n\n  subsystem\n"
                "#if FIRST\n"
                "first\n"
                "#else\n"
                "second\n"
                "#endif\n"
                "3400;\n"
                "Routine One();\n"
                "SimpleRoutine Two();\n",
                encoding="utf-8",
            )
            rows = inventory.mig_subsystem_rows(root)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_line"], "3")
        self.assertEqual(row["subsystem_names"], "first;second")
        self.assertEqual(row["routine_declarations"], "1")
        self.assertEqual(row["simpleroutine_declarations"], "1")
        self.assertEqual(row["kernel_build_roles"], "kernel_public")
        self.assertEqual(row["libsyscall_export_roles"],
                         "internal_header;public_header")

    def test_mig_parser_rejects_unterminated_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_mig_controls(root)
            source = root / "osfmk/mach/task.defs"
            source.write_text("subsystem task 3400\n", encoding="utf-8")
            with self.assertRaisesRegex(inventory.CatalogError, "no terminator"):
                inventory.mig_subsystem_rows(root)

    def test_source_manifest_admits_extracted_tree_and_rejects_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "xnu"
            manifest, document = write_fake_exact_tree(root)
            admitted, hashes, evidence = inventory.exact_source_root(root, manifest)
            self.assertEqual(admitted, root)
            self.assertEqual(evidence["defs_file_count"], 1)
            self.assertEqual(len(hashes), len(document["files"]))

            task = root / "osfmk/mach/task.defs"
            original = task.read_text(encoding="utf-8")
            task.write_text(original + "// altered\n", encoding="utf-8")
            with self.assertRaisesRegex(inventory.CatalogError, "hash differs"):
                inventory.exact_source_root(root, manifest)
            task.write_text(original, encoding="utf-8")

            added = root / "osfmk/mach/added.defs"
            added.write_text("subsystem added 9000;\n", encoding="utf-8")
            with self.assertRaisesRegex(inventory.CatalogError, "roster differs"):
                inventory.exact_source_root(root, manifest)
            added.unlink()

            task.unlink()
            with self.assertRaisesRegex(inventory.CatalogError, "source is missing"):
                inventory.exact_source_root(root, manifest)

    def test_source_manifest_rejects_duplicate_wrong_commit_and_missing_direct_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "xnu"
            manifest, document = write_fake_exact_tree(root)
            duplicate = json.loads(json.dumps(document))
            duplicate["files"].insert(1, duplicate["files"][0])
            manifest.write_bytes(inventory.source_manifest_bytes(duplicate))
            with self.assertRaisesRegex(inventory.CatalogError, "duplicate"):
                inventory.exact_source_root(root, manifest)

            manifest.write_text(
                '{"schema_version":1,"snapshot_id":"%s",'
                '"source_repository":"%s","commit":"%s","commit":"%s",'
                '"files":[]}\n' % (
                    inventory.EXACT_SNAPSHOT, inventory.SOURCE_REPOSITORY,
                    inventory.EXACT_COMMIT, inventory.EXACT_COMMIT,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(inventory.CatalogError, "duplicate key"):
                inventory.exact_source_root(root, manifest)

            wrong = json.loads(json.dumps(document))
            wrong["commit"] = "0" * 40
            manifest.write_bytes(inventory.source_manifest_bytes(wrong))
            with self.assertRaisesRegex(inventory.CatalogError, "commit differs"):
                inventory.exact_source_root(root, manifest)

            invalid_hash = json.loads(json.dumps(document))
            invalid_hash["files"][0]["sha256"] = "not-a-sha256"
            manifest.write_bytes(inventory.source_manifest_bytes(invalid_hash))
            with self.assertRaisesRegex(inventory.CatalogError, "invalid hash"):
                inventory.exact_source_root(root, manifest)

            unknown_role = json.loads(json.dumps(document))
            unknown_role["files"][0]["role"] = "invented_role"
            manifest.write_bytes(inventory.source_manifest_bytes(unknown_role))
            with self.assertRaisesRegex(inventory.CatalogError, "unknown role"):
                inventory.exact_source_root(root, manifest)

            manifest.write_bytes(inventory.source_manifest_bytes(document))
            missing = root / sorted(inventory.DIRECT_SOURCE_ROLES)[0]
            missing.unlink()
            with self.assertRaisesRegex(inventory.CatalogError, "source is missing"):
                inventory.exact_source_root(root, manifest)

    def test_source_admission_failure_writes_no_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            xnu = scratch / "xnu"
            manifest, _ = write_fake_exact_tree(xnu)
            task = xnu / "osfmk/mach/task.defs"
            task.write_text(task.read_text(encoding="utf-8") + "// altered\n",
                            encoding="utf-8")

            fields = list(inventory.SOURCE_COLUMNS)
            row = dict.fromkeys(fields, "")
            row.update({
                "snapshot_id": inventory.EXACT_SNAPSHOT,
                "family": "bsd",
                "architecture": "all",
                "number": "20",
                "logical_name": "getpid",
                "handler": "getpid",
                "status": "active",
            })
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)
            archive = scratch / "history.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("fixture/output/latest_snapshot_entries.csv",
                                output.getvalue())
            output_dir = scratch / "output"
            with contextlib.redirect_stderr(io.StringIO()):
                result = inventory.main([
                    "--archive", str(archive),
                    "--latest-xnu-root", str(xnu),
                    "--source-manifest", str(manifest),
                    "--output-dir", str(output_dir),
                    "--root", str(ROOT),
                ])
            self.assertEqual(result, 1)
            self.assertFalse(output_dir.exists())

    def test_stale_owned_outputs_are_reported_and_fail_check_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            outputs = {"darwin-syscall-inventory.json": b"{}\n"}
            stale = output / "darwin-active-syscalls-xnu-old.csv"
            stale.write_text("old\n", encoding="utf-8")
            changed, stale_paths = inventory.update_outputs(outputs, output)
            self.assertEqual(changed, [output / "darwin-syscall-inventory.json"])
            self.assertEqual(stale_paths, [stale])
            self.assertTrue(stale.is_file())
            with self.assertRaisesRegex(inventory.CatalogError, "stale owned"):
                inventory.update_outputs(outputs, output, check=True)

    def test_history_reader_rejects_bad_encoding_columns_and_snapshot(self):
        member = "fixture/output/latest_snapshot_entries.csv"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            invalid_utf8 = root / "invalid-utf8.zip"
            with zipfile.ZipFile(invalid_utf8, "w") as bundle:
                bundle.writestr(member, b"\xff\xfe")
            with self.assertRaisesRegex(inventory.CatalogError, "Cannot read"):
                inventory.read_latest_rows(invalid_utf8)

            missing_columns = root / "missing-columns.zip"
            with zipfile.ZipFile(missing_columns, "w") as bundle:
                bundle.writestr(member, "snapshot_id,family\nxnu-1.0.0,bsd\n")
            with self.assertRaisesRegex(inventory.CatalogError, "lacks columns"):
                inventory.read_latest_rows(missing_columns)

            duplicate_columns = root / "duplicate-columns.zip"
            header = ",".join(inventory.SOURCE_COLUMNS)
            with zipfile.ZipFile(duplicate_columns, "w") as bundle:
                bundle.writestr(member, header + ",snapshot_id\n")
            with self.assertRaisesRegex(inventory.CatalogError, "duplicate columns"):
                inventory.read_latest_rows(duplicate_columns)

            fields = list(inventory.SOURCE_COLUMNS)
            row = dict.fromkeys(fields, "")
            row["snapshot_id"] = "not-an-xnu-snapshot"
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)
            bad_snapshot = root / "bad-snapshot.zip"
            with zipfile.ZipFile(bad_snapshot, "w") as bundle:
                bundle.writestr(member, output.getvalue())
            with self.assertRaisesRegex(inventory.CatalogError, "invalid snapshot ID"):
                inventory.read_latest_rows(bad_snapshot)

            excess = root / "excess.zip"
            with zipfile.ZipFile(excess, "w") as bundle:
                bundle.writestr(member, output.getvalue().rstrip("\n") + ",extra\n")
            with self.assertRaisesRegex(inventory.CatalogError, "excess columns"):
                inventory.read_latest_rows(excess)

    def test_catalog_script_is_python_38_syntax(self):
        ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
