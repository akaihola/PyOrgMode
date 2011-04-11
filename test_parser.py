
import PyOrgMode
import tempfile
import time
import unittest


class TestParser(unittest.TestCase):
    """Test the org file parser with a simple org structure"""

    def setUp(self):
        """Parse the org structure from a temporary file"""
        orgfile = tempfile.NamedTemporaryFile()
        orgfile.write('\n'.join((
            '* one',
            'CLOSED: [2011-04-11 Thu 15:05]',
            '* two',
            '** two point one',
            '* three',
            '')))
        orgfile.flush()
        self.tree = PyOrgMode.DataStructure()
        try:
            self.tree.load_from_file(orgfile.name)
        finally:
            orgfile.close()

    def test_has_three_top_level_headings(self):
        """The example has three top-level headings"""
        self.assertEqual(len(self.tree.root.content), 3)

    def test_second_item_has_a_subheading(self):
        """The second top-level heading has one subheading"""
        self.assertEqual(len(self.tree.root.content[1].content), 1)

    def test_first_item_has_one_subitem(self):
        """The first top-level heading has one sub-item"""
        self.assertEqual(len(self.tree.root.content[0].content), 1)

    def test_first_item_is_closed(self):
        """The first top-level heading is closed"""
        self.assertEqual(self.tree.root.content[0].content[0].__class__,
                         PyOrgMode.Closed.Element)

    def test_first_item_closed_time(self):
        """The first top-level heading closed time is correct"""
        self.assertEqual(
            self.tree.root.content[0].content[0].timestamp,
            time.strptime('2011-04-11 15:05', '%Y-%m-%d %H:%M'))


if __name__ == '__main__':
    unittest.main()
