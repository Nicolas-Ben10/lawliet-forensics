SIGNATURES = {
    'jpeg': {
        'header': b'\xff\xd8\xff',
        'footer': b'\xff\xd9',
        'extension': 'jpg',
        'strategy': 'header_footer'
    },
    'png': {
        'header': b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a',
        'footer': b'\x49\x45\x4e\x44\xae\x42\x60\x82',
        'extension': 'png',
        'strategy': 'header_footer'
    },
    'pdf': {
        'header': b'\x25\x50\x44\x46',
        'footer': b'\x25\x25\x45\x4f\x46',
        'extension': 'pdf',
        'strategy': 'header_footer'
    },
    'gif': {
        'header': b'\x47\x49\x46\x38\x39\x61', 
        'footer': b'\x00\x3b',
        'extension': 'gif',
        'strategy': 'header_footer'
    },
    'zip': {
    'header': b'\x50\x4b\x03\x04',
    'footer': b'\x50\x4b\x05\x06',
    'extension': 'zip',
    'strategy': 'carve_zip' # own strategy
    },
    'mp4': {
        'header': b'ftyp', 
        'footer': b'\x00\x00\x00\x00\x6d\x6f\x6f\x76', #but that's not for every mp4 so we will not use
        'extension': 'mp4',
        'strategy': 'carve_mp4'
    },
    'office_new': { # that thing is exactly like a zip , but can be a xlsx and a pptx too
        'header': b'\x50\x4b\x03\x04\x14\x00\x06\x00',
        'footer': b'\x50\x4b\x05\x06',
        'extension': 'docx',
        'strategy': 'header_footer'
    }
}