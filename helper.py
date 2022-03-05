import hashlib


'''
base58 的编码字符没有小写的l和大写的I,以及大写的字母O
'''
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def encode_base58(s):
    '''
    先统计要编码的数据以多少个0开头
    '''
    count = 0
    for c in s:
        if c == 0:
            count += 1
        else:
            break

    num = int.from_bytes(s, 'big')
    prefix = '1' * count
    result = ''
    while num > 0:
        num, mod = divmod(num, 58)
        result = BASE58_ALPHABET[mod] + result

    return prefix + result

def encode_base58_checksum(b):
    '''
    实现地址编码的第4，5两步
    '''
    return encode_base58(b + hash256(b)[:4])


def hash160(s):
    return hashlib.new('ripemd160', hashlib.sha256(s).digest()).digest()

'''
在比特币应用中,哈希256都会连续执行两次以增强安全性
'''
def hash256(s):
    return hashlib.sha256(hashlib.sha256(s).digest()).digest()

'''
实现整形与小端编码的相互转换
'''
def little_endian_to_int(b):
    return int.from_bytes(b, 'little')


def int_to_little_endian(n, length):
    return n.to_bytes(length, 'little')


def read_variant(s):  # 我们假设S是一个Stream类型的对象，它支持接口read来读取各个字节
    #s.read(i)表示从输入流的当前开始处中读取第i个字符,read的作用根文件read的作用一样
    i = s.read(1)[0] #先越过1个字节，也就是版本字段，然后读取跟在版本字段后面的1个字节
    if i == 0xfd: # 如果该字节数值为253，那么读取接下来的2个字节获得输入数量
        return little_endian_to_int(s.read(2))
    elif i == 0xfe: #如果该字节为254，表示接下来4个字节用于表示输入数量
        return little_endian_to_int(s.read(4))
    elif i == 0xff: #如果该字节的值为255，表示接下来读取8个字节用于表示输入数量
        return little_endian_to_int(s.read(8))
    else:
        return i #输入数量小于253，直接读取该字节的数值表示输入数量


def encode_variant(i): # i表示输入的数量，这里对其进行编码
    if i < 0xfd: #如果值小于253，直接将其写入交易数据
        return bytes([i])
    elif i < 0x1000: # 0x1000 对于2 ^ 16, 如果数值在253 和 2 ^16 -1之间，那么前面跟着一个数值254，然后用两个字节编码i
        return b'\xfd' + int_to_little_endian(i, 2)
    elif i < 0x100000000: #0x100000000对于2^32,编码时先设置数值254，然后用4个字节编码i
        return b'\xfe' + int_to_little_endian(i, 4)
    elif i < 0x10000000000000000: #对于2^64,先设置数值255，然后用8个字符编码i
        return b'\ff' + int_to_little_endian(i, 8)
    else:
        raise ValueError('integer too large:{}'.format(i))


