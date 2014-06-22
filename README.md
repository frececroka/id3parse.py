# id3parse.py

An ID3 parser and serializer for Python 3.

## Example Usage

### Creating an ID3 tag from scratch

Input:

```python
from id3parse import ID3, ID3TextFrame

id3 = ID3.from_scratch()

id3.add_frame(ID3TextFrame.from_scratch('TIT2', 'Why Don\'t You Get A Job?'))
id3.add_frame(ID3TextFrame.from_scratch('TPE1', 'The Offspring'))

print(id3.serialize())
```

Output:

```
b'ID3\x04\x00\x00\x00\x00\x00=TIT2\x00\x00\x00\x1a\x00\x00\x03Why Don\'t You Get A Job?\x00TPE1\x00\x00\x00\x0f\x00\x00\x03The Offspring\x00'
```

### Parsing an ID3 tag

Input:

```python
from id3parse import ID3

id3 = ID3.from_byte_array(b'ID3\x04\x00\x00\x00\x00\x00=TIT2\x00\x00\x00\x1a\x00\x00\x03Why Don\'t You Get A Job?\x00TPE1\x00\x00\x00\x0f\x00\x00\x03The Offspring\x00')

for f in id3.frames:
    print(f)
```

Output:

```
TIT2: Why Don't You Get A Job?
TPE1: The Offspring
```

### Loading and saving an ID3 tag

```python
from id3parse import ID3, ID3TextFrame

id3 = ID3.from_file('01 - The Offspring - Why Dont You Get A Job.mp3')

id3.add_frame(ID3TextFrame.from_scratch('TPE1', 'The Offspring'))
id3.add_frame(ID3TextFrame.from_scratch('TIT2', 'Why Don\'t You Get A Job?'))

id3.to_file()
```

### Querying frames

```python
from id3parse import ID3, ID3TextFrame

id3 = ID3.from_file('01 - The Offspring - Why Dont You Get A Job.mp3')

tpe1 = id3.find_frame_by_name('TPE1')    # Returns a frame, fails if more than one
tpe1.text = 'The Offspring'              # frame with this name is available

privs = id3.find_frames_by_name('PRIV')  # Returns a list of frames
for priv in privs:
    print(priv)

id3.to_file()
```

## Available Frames

### ID3TextFrame

Handles `IPLS` frames and all frames beginning with `T` except `TXXX`.

#### Example Creation

```python
ID3TextFrame.from_scratch('TIT2', 'Have You Ever')
```

#### Attributes

 + `text` - The text of the frame

### ID3CommentFrame

Handles `COMM` frames.

#### Example Creation

```python
ID3CommentFrame.from_scratch('deu', 'a short description', 'the actual comment')
```

#### Attributes

 + `language` - The language of the comment
 + `description` - A short description of the comment
 + `comment` - The actual comment

### ID3PopularimeterFrame

Handles `POPM` frames.

#### Example Creation

```python
ID3PopularimeterFrame.from_scratch('john@doe.com', 106, 32)
```

#### Attributes

 + `email` - The email address of the person who rated the content
 + `rating` - The rating of the content, an integer between 0 and 255, inclusive
 + `play_counter` - A counter of arbitrary size, indicating how often the conten has been played

### ID3PlayCounterFrame

Handles `PCNT` frames.

#### Example Creation

```python
ID3PlayCounterFrame.from_scratch(32)
```

#### Attributes

 + `play_counter` - A counter of arbitrary size, indicating how often the conten has been played

### ID3UnknownFrame

Handles all frames

##### Example Creation

```python
ID3UnknownFrame.from_scratch('APIC', b'....')
```

#### Attributes

 + `raw_bytes` - The raw content of the frame body
