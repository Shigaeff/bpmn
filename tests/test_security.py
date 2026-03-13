"""Security tests — XXE, XML bomb (billion laughs), entity expansion."""

from __future__ import annotations

import pytest

from bpmn_validator.parser import BPMNParser


class TestXXEProtection:
    """Ensure the parser rejects XML External Entity attacks."""

    def test_xxe_file_entity_rejected(self, tmp_path):
        """An XXE payload referencing a local file must NOT be parsed."""
        secret = tmp_path / "secret.txt"
        secret.write_text("TOP_SECRET_DATA")

        xxe_xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///{secret.as_posix()}">
]>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true" name="&xxe;">
    <startEvent id="S1"/>
    <endEvent id="E1"/>
    <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
  </process>
</definitions>"""

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(xxe_xml)

    def test_xxe_http_entity_rejected(self):
        """An XXE payload referencing an HTTP URL must NOT be parsed."""
        xxe_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://evil.example.com/steal">
]>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true" name="&xxe;">
    <startEvent id="S1"/>
    <endEvent id="E1"/>
    <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
  </process>
</definitions>"""

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(xxe_xml)


class TestXMLBomb:
    """Ensure the parser rejects billion-laughs / entity-expansion bombs."""

    def test_billion_laughs_rejected(self):
        """A classic billion-laughs XML bomb must be rejected."""
        bomb_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true" name="&lol9;">
    <startEvent id="S1"/>
  </process>
</definitions>"""

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(bomb_xml)

    def test_recursive_entity_rejected(self):
        """Recursive entity definitions must be rejected."""
        recursive_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY a "&b;">
  <!ENTITY b "&a;">
]>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true" name="&a;">
    <startEvent id="S1"/>
  </process>
</definitions>"""

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(recursive_xml)


class TestXXEProtectionBytes:
    """Same XXE checks but using bytes input path."""

    def test_xxe_via_bytes_rejected(self):
        xxe_xml = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true" name="&xxe;">
    <startEvent id="S1"/>
  </process>
</definitions>"""

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(xxe_xml)

    def test_large_bomb_via_bytes_rejected(self):
        """Large XML bomb via bytes — huge_tree=False rejects deep expansion."""
        # 9-level bomb = 10^9 entities → guaranteed rejection by lxml
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE lolz ["]
        lines.append('  <!ENTITY lol "lol">')
        for i in range(2, 10):
            prev = f"lol{i - 1}" if i > 2 else "lol"
            refs = f"&{prev};" * 10
            lines.append(f'  <!ENTITY lol{i} "{refs}">')
        lines.append("]>")
        lines.append(
            '<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"'
            ' id="D1" targetNamespace="http://example.com">'
        )
        lines.append('  <process id="P1" isExecutable="true" name="&lol9;"/>')
        lines.append("</definitions>")
        bomb = "\n".join(lines).encode("utf-8")

        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(bomb)
