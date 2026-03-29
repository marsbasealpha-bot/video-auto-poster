"""
test_automation.py - Unit test for AI automation chain components.
"""
import os
import unittest
from unittest.mock import MagicMock, patch
from analyzer import AIAnalysisStep, MetadataStep, ThumbnailStep, RenamingStep, AutomationChain

class TestAutomationChain(unittest.TestCase):
    def setUp(self):
        self.test_video = "test_vid.mp4"
        with open(self.test_video, "w") as f:
            f.write("mock video content")

    def tearDown(self):
        for f in [self.test_video, self.test_video + ".thumb.jpg", self.test_video + ".thumbnail.jpg"]:
            if os.path.exists(f):
                os.remove(f)

    @patch('analyzer.VideoFileClip')
    @patch('analyzer.client')
    def test_ai_analysis_step(self, mock_client, mock_vfc):
        # Mock the new SDK client structure
        mock_response = MagicMock()
        mock_response.text = "A funny cat doing a flip."
        mock_client.models.generate_content.return_value = mock_response
        
        mock_clip = mock_vfc.return_value
        mock_clip.duration = 10.0
        
        step = AIAnalysisStep()
        data = {'path': self.test_video}
        
        # Mock frame saving
        with open(self.test_video + ".thumb.jpg", "w") as f:
            f.write("mock image")
            
        result = step.execute(data)
        self.assertIn('analysis', result)
        self.assertEqual(result['analysis'], "A funny cat doing a flip.")

    @patch('analyzer.client')
    def test_metadata_step_elon_tag(self, mock_client):
        mock_response = MagicMock()
        # Ensure it returns the expected structure for parsing
        mock_response.text = "HOOK\nTITLE\n#tag1 #tag2 @elonmusk"
        mock_client.models.generate_content.return_value = mock_response

        step = MetadataStep()
        data = {'analysis': 'cat flip'}
        
        result = step.execute(data)
        self.assertIn('@elonmusk', result['hashtags'])

    @patch('analyzer.os.path.exists')
    @patch('analyzer.Image.open')
    def test_thumbnail_step(self, mock_open, mock_exists):
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_img.size = (1080, 1920)
        
        step = ThumbnailStep()
        data = {'path': self.test_video, 'frame_path': self.test_video + ".thumb.jpg", 'hook': 'TEST HOOK'}
        result = step.execute(data)
        self.assertIn('thumbnail_path', result)

if __name__ == '__main__':
    unittest.main()
