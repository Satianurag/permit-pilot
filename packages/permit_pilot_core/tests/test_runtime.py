import unittest

from permit_pilot_core.platform.runtime import _parse_stream_events, extract_text


class RuntimeParseTests(unittest.TestCase):
    def test_parse_single_json_object(self) -> None:
        events = _parse_stream_events('{"content":{"parts":[{"text":"ORCH_OK"}]}}')
        self.assertEqual(len(events), 1)
        self.assertEqual(extract_text(events), "ORCH_OK")

    def test_parse_ndjson_lines(self) -> None:
        text = '{"text":"a"}\n{"text":"b"}'
        events = _parse_stream_events(text)
        self.assertEqual(len(events), 2)
        self.assertEqual(extract_text(events), "a\nb")

    def test_parse_sse_data_lines(self) -> None:
        text = 'data: {"content":{"parts":[{"text":"hello"}]}}\n\n'
        events = _parse_stream_events(text)
        self.assertEqual(len(events), 1)
        self.assertEqual(extract_text(events), "hello")


if __name__ == "__main__":
    unittest.main()
