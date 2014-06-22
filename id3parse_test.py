import unittest
import tempfile
import id3parse

class TestID3Header(unittest.TestCase):

	def test_header_creation_fails_if_wrong_test_identifier_is_present(self):
		with self.assertRaises(id3parse.ID3IllegalFormatError):
			id3parse.ID3Header.from_byte_array(b'ID4\x04\x00\x00\x00\x00\x08\x00')

	def test_header_creation_fails_if_tag_has_higher_major_version(self):
		with self.assertRaises(id3parse.ID3UnsupportedVersionError):
			id3parse.ID3Header.from_byte_array(b'ID3\x05\x00\x00\x00\x00\x08\x00')

	def test_header_creation_succeeds_if_tag_has_lower_major_version(self):
		id3parse.ID3Header.from_byte_array(b'ID3\x03\x00\x00\x00\x00\x08\x00')

	def test_header_contains_correct_flags(self):
		header = id3parse.ID3Header.from_byte_array(b'ID3\x04\x00\x50\x00\x00\x08\x00')

		self.assertFalse(header.flags.unsynced, 'Unsynchronization should not be used')
		self.assertTrue(header.flags.has_extended_header, 'A extended header should be present')
		self.assertFalse(header.flags.experimental, 'The extended flag should not be set')
		self.assertTrue(header.flags.has_footer, 'A footer should be present')

	def test_header_contains_correct_tag_size(self):
		header = id3parse.ID3Header.from_byte_array(b'ID3\x04\x00\x50\x00\x00\x08\x00')
		self.assertEqual(header.tag_size, 1024)

	def test_missing_id3_tag(self):
		with self.assertRaises(id3parse.ID3IllegalFormatError):
			header = id3parse.ID3Header.from_byte_array(b'\xff\xf3\x23\x04\x00\x50\x00\x00\x08\x00')


class TestID3(unittest.TestCase):

	test_average_case_data = b'ID3\x04\x00\x00\x00\x00\x06\x1fCOMM\x00\x00\x00\r\x00\x00\x00deu\x008E0A3B0DTSSE\x00\x00\x00H\x00\x00\x00Audiograbber 1.81.03, LAME dll 3.97, 320 Kbit/s, Stereo, Normal qualityTIT2\x00\x00\x00\x19\x00\x00\x00Why Don\'t You Get A Job?TYER\x00\x00\x00\x05\x00\x00\x001998TPUB\x00\x00\x00\t\x00\x00\x00ColumbiaTCON\x00\x00\x00\x06\x00\x00\x00(121)TALB\x00\x00\x00\n\x00\x00\x00AmericanaTRCK\x00\x00\x00\x03\x00\x00\x0011PRIV\x00\x00\x00\'\x00\x00WM/MediaClassPrimaryID\x00\xbc}`\xd1#\xe3\xe2K\x86\xa1H\xa4*(D\x1ePRIV\x00\x00\x00)\x00\x00WM/MediaClassSecondaryID\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00PRIV\x00\x00\x00\x1f\x00\x00WM/WMContentID\x00\xf5\xee\xa0\xe1\xf2x\xa9J\xb1G\xbe\xb0\xd9$k\x07PRIV\x00\x00\x00\x8a\x00\x00WM/UniqueFileIdentifier\x00A\x00M\x00G\x00a\x00_\x00i\x00d\x00=\x00R\x00 \x00 \x00 \x003\x008\x001\x006\x003\x007\x00;\x00A\x00M\x00G\x00p\x00_\x00i\x00d\x00=\x00P\x00 \x00 \x00 \x00 \x002\x006\x008\x001\x000\x00;\x00A\x00M\x00G\x00t\x00_\x00i\x00d\x00=\x00T\x00 \x00 \x002\x003\x005\x009\x007\x008\x009\x00\x00\x00TPE2\x00\x00\x00\x0e\x00\x00\x00The OffspringPRIV\x00\x00\x00"\x00\x00WM/WMCollectionID\x00\x1f\x1e\xd0\x14\xfa\xd0EG\x8d1\xfe:u\x82{\xdcPRIV\x00\x00\x00\'\x00\x00WM/WMCollectionGroupID\x00\x1f\x1e\xd0\x14\xfa\xd0EG\x8d1\xfe:u\x82{\xdcPRIV\x00\x00\x00\x14\x00\x00WM/Provider\x00A\x00M\x00G\x00\x00\x00POPM\x00\x00\x00\x1f\x00\x00Windows Media Player 9 Series\x00\xffPRIV\x00\x00\x00\x11\x00\x00AverageLevel\x00{#\x00\x00PRIV\x00\x00\x00\x0e\x00\x00PeakValue\x00\xa1\x7f\x00\x00TCOM\x00\x00\x00\x0e\x00\x00\x00The OffspringTPE1\x00\x00\x00\x0e\x00\x00\x00The Offspring'

	test_footer_data = b'ID3\x04\x00\x10\x00\x00\x00\x1aCOMM\x00\x00\x00\r\x00\x00\x00deu\x008E0A3B0D3DI\x04\x00\x10\x00\x00\x00\x1a'

	def test_average_case_deserialization(self):
		id3 = id3parse.ID3.from_byte_array(TestID3.test_average_case_data)
		self.verify_average_case_tag(id3)

	def test_average_case_serialization(self):
		id3 = id3parse.ID3.from_byte_array(TestID3.test_average_case_data)
		id3 = id3parse.ID3.from_byte_array(id3.serialize())
		self.verify_average_case_tag(id3)

	def test_serialization_with_minimal_length(self):
		id3 = id3parse.ID3.from_scratch()
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TPE1', 'The Offspring'))

		self.assertGreater(500, len(id3.serialize()))
		self.assertEqual(500, len(id3.serialize(min_length=500)))

	def verify_average_case_tag(self, id3):
		self.assertEqual(21, len(id3.body.frames))
		self.assertEqual('11', id3.find_frame_by_name('TRCK').text)
		self.assertEqual('Why Don\'t You Get A Job?', id3.find_frame_by_name('TIT2').text)
		self.assertEqual('The Offspring', id3.find_frame_by_name('TPE1').text)
		self.assertEqual('The Offspring', id3.find_frame_by_name('TPE2').text)
		self.assertEqual('The Offspring', id3.find_frame_by_name('TCOM').text)
		self.assertEqual('Americana', id3.find_frame_by_name('TALB').text)
		self.assertEqual('Audiograbber 1.81.03, LAME dll 3.97, 320 Kbit/s, Stereo, Normal quality', id3.find_frame_by_name('TSSE').text)
		self.assertEqual('(121)', id3.find_frame_by_name('TCON').text)
		self.assertEqual('Columbia', id3.find_frame_by_name('TPUB').text)
		self.assertEqual('1998', id3.find_frame_by_name('TYER').text)
		self.assertEqual('8E0A3B0D', id3.find_frame_by_name('COMM').comment)

		private_frames = id3.find_frames_by_name('PRIV')
		self.assertTrue(any(map(lambda f: f.raw_bytes == b'WM/Provider\x00A\x00M\x00G\x00\x00\x00', private_frames)))

	def test_footer(self):
		id3 = id3parse.ID3.from_scratch()
		id3.header.flags.has_footer = True
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TIT2', 'Why Don\'t You Get A Job?'))

		serialized_tag = id3.serialize()

		self.assertEqual(serialized_tag[3:10], serialized_tag[-7:])
		self.assertEqual(b'3DI', serialized_tag[-10:-7])

	def test_id3_version_3_frame_size(self):
		# ID3v2.3 stores the frame size with four bytes using all bits, while ID3v2.4 sotres the frame
		# size with four bytes using only 7 bits each. This test case should test this.
		byte_array = b'ID3\x03\x00\x00\x00\x00\x08\x4aUSLT\x00\x00\x04@\x00\x00\x00deu\x00I wrote her off for the tenth time today\r\nAnd practiced all the things I would say\r\nBut she came over\r\nI lost my nerve\r\nI took her back and made her dessert\r\nNow I know I\'m being used\r\nThat\'s okay man cause I like the abuse\r\nI know she\'s playing with me\r\nThat\'s okay cause I\'ve got no self esteem\r\nWe make plans to go out at night\r\nI wait till 2 then I turn out the light\r\nAll this rejection\'s got me so low\r\nIf she keeps it up I just might tell her so\r\nWhen she\'s saying that she wants only me\r\nThen I wonder why she sleeps with my friends\r\nWhen she\'s saying that I\'m like a disease\r\nThen I wonder how much more I can spend\r\nWell I guess I should stick up for myself\r\nBut I really think it\'s better this way\r\nThe more you suffer\r\nThe more it shows you really care Right?\r\nNow I\'ll relate this a little bit\r\nThat happens more than I\'d like to admit\r\nLate at night she knocks on my door\r\nDrunk again and looking to score\r\nNow I know I should say no\r\nBut that\'s kind of hard when she\'s ready to go\r\nI may be dumb\r\nBut I\'m not a dweeb\r\nI\'m just a sucker with no self esteem\r\nAstraLyrics'
		id3 = id3parse.ID3.from_byte_array(byte_array)

		self.assertEqual(1088, id3.find_frame_by_name('USLT').header.body_size)

	def test_serialization_with_extended_header(self):
		id3 = id3parse.ID3.from_scratch()
		id3.header.flags.has_extended_header = True

		with self.assertRaises(id3parse.ID3UnsupportedFeatureError):
			id3.serialize()

	def test_write_to_file_where_file_contains_bigger_tag(self):
		path = self.make_mp3_with_tag_and_padding()

		id3 = id3parse.ID3.from_file(path)
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TIT2', 'Welcome'))
		id3.to_file()

		self.verify_id3(path)
		self.verify_mp3(path)

	def test_write_to_file_where_file_contains_smaller_tag(self):
		path = self.make_mp3_with_tag()

		id3 = id3parse.ID3.from_file(path)
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TIT2', 'Welcome'))
		id3.to_file()

		self.verify_id3(path)
		self.verify_mp3(path)

	def test_write_to_file_where_file_contains_no_tag(self):
		path = self.make_mp3()

		id3 = id3parse.ID3.from_file(path)
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TPE1', 'The Offspring'))
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TIT2', 'Welcome'))
		id3.to_file()

		self.verify_id3(path)
		self.verify_mp3(path)

	def test_load_from_one_file_save_to_another(self):
		id3 = self.make_id3()
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TIT2', 'Welcome'))

		path = self.make_mp3_with_tag_and_padding()
		id3.to_file(path)

		self.verify_id3(path)
		self.verify_mp3(path)

	def make_mp3_with_tag_and_padding(self):
		id3 = self.make_id3()
		serialized_tag = id3.serialize(min_length=60)
		return self.make_mp3(serialized_tag)

	def make_mp3_with_tag(self):
		id3 = self.make_id3()
		serialized_tag = id3.serialize()
		return self.make_mp3(serialized_tag)

	def make_id3(self):
		id3 = id3parse.ID3.from_scratch()
		id3.add_frame(id3parse.ID3TextFrame.from_scratch('TPE1', 'The Offspring'))
		return id3

	def make_mp3(self, serialized_tag=None):
		path = tempfile.mkstemp()[1]
		f = open(path, 'wb')

		if serialized_tag is not None:
			f.write(serialized_tag)

		f.write(b'\xff\xf0...the.mp3.file...')
		f.close()

		return path

	def verify_id3(self, path):
		id3 = id3parse.ID3.from_file(path)
		self.assertEqual(2, len(id3.frames))
		self.assertEqual('Welcome', id3.find_frame_by_name('TIT2').text)
		self.assertEqual('The Offspring', id3.find_frame_by_name('TPE1').text)

	def verify_mp3(self, path):
		f = open(path, 'rb')

		byte_array = f.read()
		self.assertEqual(b'\xff\xf0...the.mp3.file...', byte_array[-20:])

		f.close()


class TestID3Frame(unittest.TestCase):

	def test_all_flags_unset(self):
		byte_array = b'TPE1\x00\x00\x00\x11\x00\x00\x03Die Toten Hosen\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertFalse(frame.header.status_flags.keep_on_tag_modification)
		self.assertFalse(frame.header.status_flags.keep_on_file_modification)
		self.assertFalse(frame.header.status_flags.read_only)

		self.assertFalse(frame.header.format_flags.has_grouping_id)
		self.assertFalse(frame.header.format_flags.compressed)
		self.assertFalse(frame.header.format_flags.encrypted)
		self.assertFalse(frame.header.format_flags.unsynced)
		self.assertFalse(frame.header.format_flags.has_data_length_indicator)

	def test_frame_name(self):
		byte_array = b'TPE1\x00\x00\x00\x11\x00\x00\x03Die Toten Hosen\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('TPE1', frame.name)

	def test_frame_name_which_is_too_short(self):
		with self.assertRaises(id3parse.ID3IllegalFormatError):
			byte_array = b'TPE\x00\x00\x00\x11\x00\x00\x03Die Toten Hosen\x00'
			frame = id3parse.ID3Frame.from_byte_array(byte_array)

	def test_grouping_identity(self):
		byte_array = b'TPE1\x00\x00\x00\x11\x00\x40\x10\x03Die Toten Hosen\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertTrue(frame.header.format_flags.has_grouping_id)
		self.assertEqual(0x10, frame.header.grouping_id)

	def test_deunsynchronization(self):
		byte_array = b'TPE1\x00\x00\x00\x14\x00\x02\x01\xff\x00\xfeR\x00\xe9\x00n\x00a\x00u\x00l\x00t\x00\x00\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_deunsynchronization_with_data_length_indicator(self):
		byte_array = b'TPE1\x00\x00\x00\x18\x00\x03\x00\x00\x00\x17\x01\xff\x00\xfeR\x00\xe9\x00n\x00a\x00u\x00l\x00t\x00\x00\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)
		self.assertEqual(0x18, frame.header.body_size)
		self.assertEqual(0x17, frame.header.uncompressed_body_size)

	def test_unsynchronisation(self):
		frame_data = b'A....\xff\xf0.......\xff\x00.....O'

		frame = id3parse.ID3UnknownFrame.from_scratch('PRIV', frame_data)
		frame.header.format_flags.unsynced = True

		serialized_frame = frame.serialize()
		self.assertNotIn(b'\xff\xf0', serialized_frame)

		frame = id3parse.ID3Frame.from_byte_array(serialized_frame)
		self.assertEqual(frame_data, frame.raw_bytes)

	def test_frame_with_only_a_single_byte(self):
		frame = id3parse.ID3Frame.from_byte_array(b'TRCK\x00\x00\x00\x01\x00\x00\x00')
		self.assertEqual('', frame.text)

	def test_unsupported_feature_compression(self):
		with self.assertRaises(id3parse.ID3UnsupportedFeatureError):
			byte_array = b'TPE1\x00\x00\x00\x11\x00\x08\x03Die Toten Hosen\x00'
			id3parse.ID3Frame.from_byte_array(byte_array)

	def test_unsupported_feature_encryption(self):
		with self.assertRaises(id3parse.ID3UnsupportedFeatureError):
			byte_array = b'TPE1\x00\x00\x00\x11\x00\x04\x03Die Toten Hosen\x00'
			id3parse.ID3Frame.from_byte_array(byte_array)


class TestID3TextFrame(unittest.TestCase):

	def test_utf8_encoded_frame(self):
		byte_array = b'TPE1\x00\x00\x00\x0a\x00\x00\x03R\xc3\xa9nault\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_utf16_encoded_frame(self):
		byte_array = b'TPE1\x00\x00\x00\x13\x00\x00\x01\xff\xfeR\x00\xe9\x00n\x00a\x00u\x00l\x00t\x00\x00\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_utf16_be_encoded_frame(self):
		byte_array = b'TPE1\x00\x00\x00\x11\x00\x00\x02\x00R\x00\xe9\x00n\x00a\x00u\x00l\x00t\x00\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_latin1_encoded_frame(self):
		byte_array = b'TPE1\x00\x00\x00\x09\x00\x00\x00R\xe9nault\x00'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_frame_with_unknown_encoding(self):
		with self.assertRaises(id3parse.ID3IllegalFormatError):
			byte_array = b'TPE1\x00\x00\x00\x09\x00\x00\x04R\xe9nault\x00'
			frame = id3parse.ID3Frame.from_byte_array(byte_array)

	def test_frame_with_unterminated_string(self):
		byte_array = b'TPE1\x00\x00\x00\x09\x00\x00\x00R\xe9nault'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('Rénault', frame.text)

	def test_serialization(self):
		frame = id3parse.ID3TextFrame.from_scratch('TIT2', 'Caught Me Thinking')
		self.assertEqual(b'TIT2\x00\x00\x00\x14\x00\x00\x03Caught Me Thinking\x00', frame.serialize())

	def test_creation_from_scratch_with_illegal_frame_name(self):
		with self.assertRaises(ValueError):
			id3parse.ID3TextFrame.from_scratch('ABCD', 'Caught Me Thinking')


class TestID3CommentFrame(unittest.TestCase):

	def test_average_case(self):
		byte_array = b'COMM\x00\x00\x00\x2a\x00\x00\x00deua short description\x00the actual comment'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual('deu', frame.language)
		self.assertEqual('a short description', frame.description)
		self.assertEqual('the actual comment', frame.comment)

	def test_serialization(self):
		frame = id3parse.ID3CommentFrame.from_scratch('deu', 'a short description', 'the actual comment')
		self.assertEqual(b'COMM\x00\x00\x00\x2a\x00\x00\x03deua short description\x00the actual comment', frame.serialize())


class TestID3PopularimeterFrame(unittest.TestCase):

	def test_serialization(self):
		frame = id3parse.ID3PopularimeterFrame.from_scratch('user@localhost', 128, 30)

		self.assertEqual(b'POPM\x00\x00\x00\x14\x00\x00user@localhost\x00\x80\x00\x00\x00\x1e', frame.serialize())

	def test_serialization_of_large_play_counter(self):
		frame = id3parse.ID3PopularimeterFrame.from_scratch('user@localhost', 128, 9999999999)

		self.assertEqual(b'POPM\x00\x00\x00\x15\x00\x00user@localhost\x00\x80\x02\x54\x0b\xe3\xff', frame.serialize())

	def test_deserialization(self):
		frame = id3parse.ID3Frame.from_byte_array(b'POPM\x00\x00\x00\x14\x00\x00user@localhost\x00\x80\x00\x00\x00\x1e')

		self.assertEqual('user@localhost', frame.email)
		self.assertEqual(128, frame.rating)
		self.assertEqual(30, frame.play_counter)

	def test_deserialization_of_large_play_counter(self):
		frame = id3parse.ID3Frame.from_byte_array(b'POPM\x00\x00\x00\x15\x00\x00user@localhost\x00\x80\x02\x54\x0b\xe3\xff')
		self.assertEqual(9999999999, frame.play_counter)

	def test_rating_overflow(self):
		frame = id3parse.ID3PopularimeterFrame.from_scratch('user@localhost', 128, 30)

		with self.assertRaises(ValueError):
			frame.rating = 256

	def test_rating_underflow(self):
		frame = id3parse.ID3PopularimeterFrame.from_scratch('user@localhost', 128, 30)

		with self.assertRaises(ValueError):
			frame.rating = -1


class TestID3PlayCounterFrame(unittest.TestCase):

	def test_serialization(self):
		frame = id3parse.ID3PlayCounterFrame.from_scratch(30)

		self.assertEqual(b'PCNT\x00\x00\x00\x04\x00\x00\x00\x00\x00\x1e', frame.serialize())

	def test_deserialization(self):
		frame = id3parse.ID3Frame.from_byte_array(b'PCNT\x00\x00\x00\x04\x00\x00\x00\x00\x00\x1e')
		self.assertEqual(30, frame.play_counter)

	def test_serialization_of_large_play_counter(self):
		frame = id3parse.ID3PlayCounterFrame.from_scratch(9999999999)

		self.assertEqual(b'PCNT\x00\x00\x00\x05\x00\x00\x02\x54\x0b\xe3\xff', frame.serialize())

	def test_deserialization_of_large_play_counter(self):
		frame = id3parse.ID3Frame.from_byte_array(b'PCNT\x00\x00\x00\x05\x00\x00\x02\x54\x0b\xe3\xff')
		self.assertEqual(9999999999, frame.play_counter)


class TestID3UnknownFrame(unittest.TestCase):

	def test_average_case(self):
		byte_array = b'ABCD\x00\x00\x00\x27\x00\x00WM/MediaClassPrimaryID\x00\xbc}`\xd1#\xe3\xe2K\x86\xa1H\xa4*(D\x1e'
		frame = id3parse.ID3Frame.from_byte_array(byte_array)

		self.assertEqual(byte_array, frame.serialize())


class TestID3FrameHeader(unittest.TestCase):

	def test_base_frame_header(self):
		byte_array = b'ABCD\x00\x00\x00\x27\x00\x00'
		frame_header = id3parse.ID3FrameHeader.from_byte_array(byte_array)

		self.assertEqual(39, frame_header.body_size)
		self.assertEqual(10, frame_header.size)

		self.assertFalse(frame_header.status_flags.keep_on_tag_modification)
		self.assertFalse(frame_header.status_flags.keep_on_file_modification)
		self.assertFalse(frame_header.status_flags.read_only)

		self.assertFalse(frame_header.format_flags.has_grouping_id)
		self.assertFalse(frame_header.format_flags.compressed)
		self.assertFalse(frame_header.format_flags.encrypted)
		self.assertFalse(frame_header.format_flags.has_data_length_indicator)

	def test_frame_header_with_appended_information(self):
		byte_array = b'ABCD\x00\x00\x00\x27\x00\x41\xab\x00\x00\x00\x27'
		frame_header = id3parse.ID3FrameHeader.from_byte_array(byte_array)

		self.assertEqual(15, frame_header.size)
		self.assertEqual(171, frame_header.grouping_id)
		self.assertEqual(0x27, frame_header.uncompressed_body_size)

class TestPackAndUnpackInteger(unittest.TestCase):

	def test_pack_integer_smaller_than_base(self):
		packed_integer = id3parse.pack_int(101, base=128, min_bytes=4)
		self.assertEqual(b'\x00\x00\x00\x65', packed_integer)

	def test_pack_integer_bigger_than_base(self):
		packed_integer = id3parse.pack_int(8008, base=128, min_bytes=4)
		self.assertEqual(b'\x00\x00\x3e\x48', packed_integer)

	def test_pack_integer_zero(self):
		packed_integer = id3parse.pack_int(0, base=128, min_bytes=4)
		self.assertEqual(b'\x00\x00\x00\x00', packed_integer)

	def test_unpack_integer(self):
		integer = 459234643

		packed_integer = id3parse.pack_int(integer, base=128)
		unpacked_integer = id3parse.unpack_int(packed_integer, base=128)

		self.assertEqual(integer, unpacked_integer)


class TestSetAndGetFlag(unittest.TestCase):

	def test_pack_and_get_flags(self):
		flags_byte = id3parse.pack_flags((True, False, True, True, False, False, False, True))[0]

		self.assertTrue(id3parse.get_flag(flags_byte, 7))
		self.assertFalse(id3parse.get_flag(flags_byte, 6))
		self.assertTrue(id3parse.get_flag(flags_byte, 5))
		self.assertTrue(id3parse.get_flag(flags_byte, 4))
		self.assertFalse(id3parse.get_flag(flags_byte, 3))
		self.assertFalse(id3parse.get_flag(flags_byte, 2))
		self.assertFalse(id3parse.get_flag(flags_byte, 1))
		self.assertTrue(id3parse.get_flag(flags_byte, 0))


class TestTerminatedStrings(unittest.TestCase):

	def test_extract_terrminated_string_with_single_zero_as_terminator(self):
		terminated_string = b'The quick brown fox jumps over the lazy dog\x00andsomegarbage'
		string = id3parse.extract_terminated_string(terminated_string, b'\x00')

		self.assertEqual(b'The quick brown fox jumps over the lazy dog', string)

	def test_extract_terrminated_string_with_double_zero_as_terminator(self):
		terminated_string = 'The quick brown fox jumps over the lazy dog'.encode('utf-16') + b'\x00\x00andsomegarbage'
		encoded_string = id3parse.extract_terminated_string(terminated_string, b'\x00\x00')
		string = encoded_string.decode('utf-16')

		self.assertEqual('The quick brown fox jumps over the lazy dog', string)

	def test_extract_terminated_string_with_missing_terminator(self):
		with self.assertRaises(ValueError):
			terminated_string = 'The quick brown fox jumps over the lazy dog'.encode('utf-16')
			id3parse.extract_terminated_string(terminated_string, b'\x00\x00')

	def test_extract_terminated_string_with_empty_string(self):
		terminated_string = b'\x00and some content after the terminator'
		string = id3parse.extract_terminated_string(terminated_string, b'\x00')

		self.assertEqual(b'', string)
