import re
import math

def pack_int(integer, base, min_bytes=1):
	if integer == 0:
		return b'\x00' * min_bytes

	byte_array = bytearray()
	exponent = math.floor(math.log(integer, base))

	for _ in range(max(0, min_bytes - exponent - 1)):
		byte_array.append(0)

	while exponent >= 0:
		t = math.pow(base, exponent)

		digit = math.floor(integer / t)
		integer -= digit * t

		byte_array.append(digit)
		exponent -= 1

	return byte_array

def unpack_int(digits, base):
	integer = 0
	exponent = len(digits) - 1

	for digit in digits:
		integer += digit * pow(base, exponent)
		exponent -= 1

	return integer

def get_flag(byte, position):
	return (byte >> position) & 1 == 1

def set_flag(byte, position):
	return byte | 1 << position

def pack_flags(flags):
	if len(flags) != 8:
		raise ValueError('Need 8 flags to pack into one byte, but got %d' % len(flags))

	flags_byte = 0
	for i, f in enumerate(flags):
		if f:
			flags_byte = set_flag(flags_byte, 7 - i)

	return bytes([flags_byte])

def decode_text_encoding(e):
	encodings = {
		0x00: 'iso-8859-1',
		0x01: 'utf-16',
		0x02: 'utf-16-be',
		0x03: 'utf-8'
	}

	terminators = {
		0x00: b'\x00',
		0x01: b'\x00\x00',
		0x02: b'\x00\x00',
		0x03: b'\x00'
	}

	try:
		return encodings[e], terminators[e]
	except KeyError:
		raise ID3IllegalFormatError('Unknown text encoding "0x%02x"' % e)

def unsync(byte_array):
	def is_false_sync(current_byte, next_byte):
		return current_byte == 0xff and (next_byte == 0x00 or next_byte > 0xe0)

	unsynced_byte_array = bytearray()

	for i in range(len(byte_array)):
		current_byte = byte_array[i]
		unsynced_byte_array.append(current_byte)

		if i + 1 < len(byte_array):
			next_byte = byte_array[i+1]
			if is_false_sync(current_byte, next_byte):
				unsynced_byte_array.append(0x00)

	return unsynced_byte_array

def deunsync(byte_array):
	return byte_array.replace(b'\xff\x00', b'\xff')

def extract_terminated_string(byte_array, terminator):
	def find_indexes(byte_array, terminator):
		start = 0
		while True:
			terminator_index = byte_array.index(terminator, start)
			yield terminator_index

			start = terminator_index + 1

	for terminator_index in find_indexes(byte_array, terminator):
		if terminator_index % len(terminator) == 0:
			return byte_array[0:terminator_index]


class ByteReader:

	def __init__(self, byte_array):
		self.byte_array = byte_array

	def peek(self, n=1):
		bts = self.byte_array[0:n]

		if n == 1:
			return bts[0]
		else:
			return bts

	def read(self, n=1):
		bts = self.peek(n)
		self.skip(n)

		return bts

	def skip(self, n):
		self.byte_array = self.byte_array[n:]

	def tail(self):
		return self.byte_array

	def clone(self, n=None):
		if n is None:
			return ByteReader(self.tail())
		else:
			return ByteReader(self.read(n))

	def bytes_left(self):
		return len(self.byte_array)


TAG_HEADER_SIZE = 10
FRAME_HEADER_SIZE = 10
FOOTER_SIZE = 10
SUPPORTED_MAJOR_VERSION = 4

SYNCHSAFE_BASE = 128
DEFAULT_BASE = 256


class ID3:

	def from_byte_array(byte_array):
		br = ByteReader(byte_array)

		header = ID3Header.from_byte_reader(br.clone(TAG_HEADER_SIZE))
		body_size = header.tag_size

		extended_header = None
		if header.flags.has_extended_header:
			extended_header = ID3ExtendedHeader.from_byte_reader(br.clone())
			br.skip(extended_header.size)
			body_size -= extended_header.size

		body = ID3Body.from_byte_reader(br.clone(body_size), tag_version=header.major_version)
		return ID3(header, body)

	def from_input_stream(input_stream):
		total_bytes = input_stream.read(TAG_HEADER_SIZE)
		header = ID3Header.from_byte_array(total_bytes)

		# ID3 body
		total_bytes += input_stream.read(header.tag_size)

		if header.flags.has_footer:
			total_bytes += input_stream.read(FOOTER_SIZE)

		return ID3.from_byte_array(total_bytes)

	def from_file(path):
		file = open(path, 'rb')

		try:
			id3 = ID3.from_input_stream(file)
		except ID3IllegalFormatError:
			id3 = ID3.from_scratch()

		id3.initial_path = path

		file.close()
		return id3

	def from_scratch():
		header = ID3Header.from_scratch()
		body = ID3Body.from_scratch()

		return ID3(header, body)

	def __init__(self, header, body):
		self.header = header
		self.body = body

	@property
	def frames(self):
		return self.body.frames

	def find_frame_by_name(self, name):
		return self.body.find_frame_by_name(name)

	def find_frames_by_name(self, name):
		return self.body.find_frames_by_name(name)

	def add_frame(self, frame):
		self.body.add_frame(frame)

	def serialize(self, min_length=0):
		if self.header.flags.has_extended_header:
			raise ID3UnsupportedFeatureError('Extended header not supported during serialization.')

		body_bytes = self.body.serialize()

		min_length -= TAG_HEADER_SIZE
		if len(body_bytes) < min_length:
			body_bytes += b'\x00' * (min_length - len(body_bytes))

		self.header.tag_size = len(body_bytes)

		footer_bytes = b''
		if self.header.flags.has_footer:
			footer_bytes = self.header.serialize_footer()

		header_bytes = self.header.serialize_header()

		return header_bytes + body_bytes + footer_bytes

	def to_file(self, path=None):
		path = path or self.initial_path
		if path is None:
			raise ValueError('Path must be given if saving a tag which was not loaded from a file')

		f = open(path, 'r+b')

		serialized_tag = self.serialize()
		current_tag_size = len(serialized_tag)

		try:
			existing_header = ID3Header.from_byte_array(f.read(TAG_HEADER_SIZE))
			initial_tag_size = existing_header.tag_size + TAG_HEADER_SIZE
		except ID3IllegalFormatError:
			initial_tag_size = 0

		def write_tag():
			f.seek(0)
			f.write(serialized_tag)

		def write_padding():
			padding_length = initial_tag_size - current_tag_size
			padding = b'\x00' * padding_length
			f.write(padding)

		def read_mp3():
			f.seek(initial_tag_size)
			return f.read()

		if current_tag_size <= initial_tag_size:
			write_tag()
			write_padding()
		else:
			mp3_content = read_mp3()
			write_tag()
			f.write(mp3_content)

		f.close()


class ID3Header:

	def from_byte_array(byte_array):
		if len(byte_array) != TAG_HEADER_SIZE:
			raise ID3IllegalFormatError(
				'Header must be %d bytes, but was %d bytes' % (TAG_HEADER_SIZE, len(byte_array))
			)

		return ID3Header.from_byte_reader(ByteReader(byte_array))

	def from_byte_reader(br):
		identifier = br.read(3)
		if identifier != b'ID3':
			raise ID3IllegalFormatError(
				'ID3 identifier has to be "ID3", but was "%s"' % identifier
			)

		major_version = br.read()
		minor_version = br.read()
		if major_version > SUPPORTED_MAJOR_VERSION:
			raise ID3UnsupportedVersionError(
				'Unsupported major version: ID3v2.%d.%d' % (major_version, minor_version)
			)

		flags = ID3HeaderFlags.from_byte(br.read())
		tag_size = unpack_int(br.read(4), base=SYNCHSAFE_BASE)

		return ID3Header(flags, tag_size, major_version)

	def from_scratch():
		flags = ID3HeaderFlags()
		return ID3Header(flags)

	def __init__(self, flags, tag_size=0, major_version=4):
		self.tag_size = tag_size
		self.flags = flags
		self.major_version = major_version

	def serialize_header(self):
		return self.serialize(b'ID3')

	def serialize_footer(self):
		return self.serialize(b'3DI')

	def serialize(self, identifier):
		return identifier + b'\x04\x00' + self.flags.serialize() + pack_int(self.tag_size, base=SYNCHSAFE_BASE, min_bytes=4)


class ID3HeaderFlags:

	def from_byte(packedFlags):
		header_flags = ID3HeaderFlags()

		header_flags.unsynced = get_flag(packedFlags, 7)
		header_flags.has_extended_header = get_flag(packedFlags, 6)
		header_flags.experimental = get_flag(packedFlags, 5)
		header_flags.has_footer = get_flag(packedFlags, 4)

		return header_flags

	def __init__(self):
		self.unsynced = False
		self.has_extended_header = False
		self.experimental = False
		self.has_footer = False

	def serialize(self):
		return pack_flags((
			self.unsynced,
			self.has_extended_header,
			self.experimental,
			self.has_footer,
			False,
			False,
			False,
			False
		))


class ID3ExtendedHeader:

	def from_byte_array(byte_array):
		return ID3ExtendedHeader.from_byte_reader(ByteReader(byte_array))

	def from_byte_reader(br):
		size = unpack_int(br.read(4), base=SYNCHSAFE_BASE)
		return ID3ExtendedHeader(size)

	def __init__(self, size):
		self.size = size


class ID3Body:

	def from_byte_array(byte_array, tag_version):
		return ID3Body.from_byte_reader(ByteReader(byte_array), tag_version)

	def from_byte_reader(br, tag_version):
		frames = []
		while br.bytes_left() > 0 and br.peek() != 0:
			frame = ID3Frame.from_byte_reader(br.clone(), tag_version=tag_version)
			br.skip(FRAME_HEADER_SIZE + frame.header.body_size)

			frames.append(frame)

		return ID3Body(frames)

	def from_scratch():
		return ID3Body([])

	def __init__(self, frames):
		self.frames = frames

	def find_frame_by_name(self, name):
		matching_frames = self.find_frames_by_name(name)

		if len(matching_frames) > 1:
			raise ValueError('More than one frame matched the given name. Use ID3Body.find_frames_by_name instead.')

		if len(matching_frames) == 0:
			raise ValueError('No frame matched the given name.')

		return matching_frames[0]

	def find_frames_by_name(self, name):
		return [f for f in self.frames if f.name == name]

	def add_frame(self, frame):
		self.frames.append(frame)

	def serialize(self):
		byte_array = b''

		for f in self.frames:
			byte_array += f.serialize()

		return byte_array


class ID3Frame:

	id3_frame_implementations = []

	def from_byte_array(byte_array, tag_version=4):
		return ID3Frame.from_byte_reader(ByteReader(byte_array), tag_version)

	def from_byte_reader(br, tag_version):
		header = ID3FrameHeader.from_byte_reader(br.clone(), tag_version=tag_version)
		br.skip(header.size)

		body_bytes = br.read(header.body_size)
		if header.format_flags.unsynced:
			body_bytes = deunsync(body_bytes)

		ID3FrameImplementation = next((f for f in ID3Frame.id3_frame_implementations if f.can_handle(header.name)), ID3UnknownFrame)
		return ID3FrameImplementation.from_byte_array(header, body_bytes)

	def __init__(self, header):
		self.header = header
		self.name = header.name

	def serialize(self):
		serialized_body = self.serialize_body()
		if self.header.format_flags.unsynced:
			serialized_body = unsync(serialized_body)

		self.header.body_size = len(serialized_body)
		serialized_header = self.header.serialize()

		return serialized_header + serialized_body


class ID3FrameHeader:

	def from_byte_array(byte_array, tag_version=4):
		return ID3FrameHeader.from_byte_reader(ByteReader(byte_array), tag_version)

	def from_byte_reader(br, tag_version):
		name = br.read(4).decode('ascii')

		body_size_bytes = br.read(4)
		body_size = 0
		if tag_version == 4:
			body_size = unpack_int(body_size_bytes, base=SYNCHSAFE_BASE)
		else:
			body_size = unpack_int(body_size_bytes, base=DEFAULT_BASE)

		status_flags = ID3FrameStatusFlags.from_byte(br.read())
		format_flags = ID3FrameFormatFlags.from_byte(br.read())

		total_size = FRAME_HEADER_SIZE

		grouping_id = None
		if format_flags.has_grouping_id:
			grouping_id = br.read()
			total_size += 1

		uncompressed_body_size = None
		if format_flags.has_data_length_indicator:
			uncompressed_body_size = unpack_int(br.read(4), base=SYNCHSAFE_BASE)
			total_size += 4

		if format_flags.compressed:
			raise ID3UnsupportedFeatureError('Compression of frames is currently not supported')

		if format_flags.encrypted:
			raise ID3UnsupportedFeatureError('Encryption of frames is currently not supported')

		return ID3FrameHeader(
			name,
			total_size,
			body_size,
			status_flags,
			format_flags,
			uncompressed_body_size,
			grouping_id
		)

	def from_name(name):
		default_status_flags = ID3FrameStatusFlags()
		default_format_flags = ID3FrameFormatFlags()

		return ID3FrameHeader(name, None, None, default_status_flags, default_format_flags, None, None)

	def __init__(self, name, size, body_size, status_flags, format_flags, uncompressed_body_size, grouping_id):
		self.name = name
		self.size = size
		self.body_size = body_size

		self.status_flags = status_flags
		self.format_flags = format_flags

		self.grouping_id = grouping_id
		self.uncompressed_body_size = uncompressed_body_size

	def serialize(self):
		serialized_frame_name = self.name.encode('ascii')
		serialized_body_size = pack_int(self.body_size, base=SYNCHSAFE_BASE, min_bytes=4)
		serialized_status_flags = self.status_flags.serialize()
		serialized_format_flags = self.format_flags.serialize()

		return serialized_frame_name + serialized_body_size + serialized_status_flags + serialized_format_flags


class ID3FrameStatusFlags:

	def from_byte(packedFlags):
		frame_status_flags = ID3FrameStatusFlags()

		frame_status_flags.keep_on_tag_modification = get_flag(packedFlags, 6)
		frame_status_flags.keep_on_file_modification = get_flag(packedFlags, 5)
		frame_status_flags.read_only = get_flag(packedFlags, 4)

		return frame_status_flags

	def __init__(self):
		self.keep_on_tag_modification = False
		self.keep_on_file_modification = False
		self.read_only = False

	def serialize(self):
		return pack_flags((
			False,
			self.keep_on_tag_modification,
			self.keep_on_file_modification,
			self.read_only,
			False,
			False,
			False,
			False
		))


class ID3FrameFormatFlags:

	def from_byte(packedFlags):
		frame_format_flags = ID3FrameFormatFlags()

		frame_format_flags.has_grouping_id = get_flag(packedFlags, 6)
		frame_format_flags.compressed = get_flag(packedFlags, 3)
		frame_format_flags.encrypted = get_flag(packedFlags, 2)
		frame_format_flags.unsynced = get_flag(packedFlags, 1)
		frame_format_flags.has_data_length_indicator = get_flag(packedFlags, 0)

		return frame_format_flags

	def __init__(self):
		self.has_grouping_id = False
		self.compressed = False
		self.encrypted = False
		self.unsynced = False
		self.has_data_length_indicator = False

	def serialize(self):
		return pack_flags((
			False,
			self.has_grouping_id,
			False,
			False,
			self.compressed,
			self.encrypted,
			self.unsynced,
			self.has_data_length_indicator
		))


class ID3TextFrame(ID3Frame):

	def can_handle(name):
		if name[0] == 'T' and name != 'TXXX':
			return True

		if name == 'IPLS':
			return True

		return False

	def from_byte_array(header, byte_array):
		br = ByteReader(byte_array)

		encoding_byte = br.read()
		encoding, terminator = decode_text_encoding(encoding_byte)

		encoded_text = ID3TextFrame.get_encoded_text(br.tail(), terminator)
		text = encoded_text.decode(encoding)

		return ID3TextFrame(header, text)

	def get_encoded_text(byte_array, terminator):
		try:
			return extract_terminated_string(byte_array, terminator)
		except ValueError:
			return byte_array

	def from_scratch(name, text):
		if not ID3TextFrame.can_handle(name):
			raise ValueError('ID3TextFrame cannot handle frame name "%s"' % name)

		header = ID3FrameHeader.from_name(name)
		return ID3TextFrame(header, text)

	def __init__(self, header, text):
		super(ID3TextFrame, self).__init__(header)
		self.text = text

	def serialize_body(self):
		encoding = b'\x03'
		string_terminator = b'\x00'

		return encoding + self.text.encode('utf-8') + string_terminator

	def __str__(self):
		return self.name + ': ' + self.text


ID3Frame.id3_frame_implementations.append(ID3TextFrame)


class ID3CommentFrame(ID3Frame):

	def can_handle(name):
		return name == 'COMM'

	def from_byte_array(header, byte_array):
		br = ByteReader(byte_array)

		encoding_byte = br.read()
		encoding, terminator = decode_text_encoding(encoding_byte)

		language = br.read(3).decode('iso-8859-1')

		encoded_description = extract_terminated_string(br.tail(), terminator)
		description = encoded_description.decode(encoding)

		br.skip(len(encoded_description) + len(terminator))
		encoded_comment = br.tail()
		comment = encoded_comment.decode(encoding)

		return ID3CommentFrame(header, language, description, comment)

	def from_scratch(language, description, comment):
		header = ID3FrameHeader.from_name('COMM')
		return ID3CommentFrame(header, language, description, comment)

	def __init__(self, header, language, description, comment):
		super(ID3CommentFrame, self).__init__(header)

		self.header = header
		self.language = language
		self.description = description
		self.comment = comment

	def serialize_body(self):
		encoding = b'\x03'
		language = self.language.encode('ascii')
		description = self.description.encode('utf-8') + b'\x00'
		comment = self.comment.encode('utf-8')

		return encoding + language + description + comment

	def __str__(self):
		return self.name + ': ' + self.comment


ID3Frame.id3_frame_implementations.append(ID3CommentFrame)


class ID3PopularimeterFrame(ID3Frame):

	def can_handle(name):
		return name == 'POPM'

	def from_byte_array(header, byte_array):
		br = ByteReader(byte_array)

		encoded_email = extract_terminated_string(br.tail(), b'\x00')
		email = encoded_email.decode('iso-8859-1')
		br.skip(len(encoded_email + b'\x00'))

		rating = br.read()
		play_counter = unpack_int(br.tail(), base=DEFAULT_BASE)

		return ID3PopularimeterFrame(header, email, rating, play_counter)

	def from_scratch(email, rating, play_counter):
		header = ID3FrameHeader.from_name('POPM')
		return ID3PopularimeterFrame(header, email, rating, play_counter)

	def __init__(self, header, email, rating, play_counter):
		super(ID3PopularimeterFrame, self).__init__(header)

		self.email = email
		self.rating = rating
		self.play_counter = play_counter

	@property
	def rating(self):
		return self._rating

	@rating.setter
	def rating(self, rating):
		if rating < 0 or rating > 255:
			raise ValueError('Rating must be between 0 and 255, inclusive.')

		self._rating = rating

	def serialize_body(self):
		email = self.email.encode('iso-8859-1') + b'\x00'
		rating = pack_int(self.rating, base=DEFAULT_BASE, min_bytes=1)
		play_counter = pack_int(self.play_counter, base=DEFAULT_BASE, min_bytes=4)

		return email + rating + play_counter


ID3Frame.id3_frame_implementations.append(ID3PopularimeterFrame)


class ID3PlayCounterFrame(ID3Frame):

	def can_handle(name):
		return name == 'PCNT'

	def from_byte_array(header, byte_array):
		play_counter = unpack_int(byte_array, base=DEFAULT_BASE)
		return ID3PlayCounterFrame(header, play_counter)

	def from_scratch(play_counter):
		header = ID3FrameHeader.from_name('PCNT')
		return ID3PlayCounterFrame(header, play_counter)

	def __init__(self, header, play_counter):
		super(ID3PlayCounterFrame, self).__init__(header)
		self.play_counter = play_counter

	def serialize_body(self):
		return pack_int(self.play_counter, base=DEFAULT_BASE, min_bytes=4)


ID3Frame.id3_frame_implementations.append(ID3PlayCounterFrame)


class ID3UnknownFrame(ID3Frame):

	def from_byte_array(header, byte_array):
		return ID3UnknownFrame(header, byte_array)

	def from_scratch(name, raw_bytes):
		header = ID3FrameHeader.from_name(name)
		return ID3UnknownFrame(header, raw_bytes)

	def __init__(self, header, raw_bytes):
		super(ID3UnknownFrame, self).__init__(header)
		self.raw_bytes = raw_bytes

	def serialize_body(self):
		return self.raw_bytes

	def __str__(self):
		return self.name + ': ' + str(self.raw_bytes[0:20])


class ID3Error(Exception):

	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)


class ID3IllegalFormatError(ID3Error):

	def __init__(self, value):
		super(ID3IllegalFormatError, self).__init__(value)

	def __str__(self):
		return repr(self.value)


class ID3UnsupportedVersionError(ID3Error):

	def __init__(self, value):
		super(ID3UnsupportedVersionError, self).__init__(value)

	def __str__(self):
		return repr(self.value)


class ID3UnsupportedFeatureError(ID3Error):

	def __init__(self, value):
		super(ID3UnsupportedFeatureError, self).__init__(value)

	def __str__(self):
		return repr(self.value)
