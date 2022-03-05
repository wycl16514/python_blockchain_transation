from helper import *
import requests
from io import BytesIO

class Transation:
    def __init__(self, version, inputs, outputs, lock_time, test_net = False):
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.lock_time = lock_time
        self.test_net = test_net

    def __repr__(self):
        inputs = ''
        for input in self.inputs:
            inputs += input.__repr__() + '\n'

        outputs = ''
        for output in self.outputs:
            outputs += output.__repr__() + "\n"

        return f"tx: {self.id()}\nversion:{self.version}\ninputs:{inputs}\noutputs:{outputs}\nlock_time:{self.lock_time}"

    def id(self):
        return self.hash().hex()

    def hash(self):
        return hash256(self.serialize())[::-1]

    @classmethod
    def parse(cls, s, testnet = False):
        version = little_endian_to_int(s.read(4))
        num_inputs = read_variant(s)
        inputs = []
        for _ in range(num_inputs):
            inputs.append(TxIn.parse(s))

        outputs = []
        num_outputs = read_variant(s)
        for _ in range(num_outputs):
            outputs.append(TxOut.parse(s))

        lock_time = little_endian_to_int(s.read(4)) # 最后4字节是lock time
        return cls(version, inputs, outputs, lock_time, testnet = testnet)

    def serialize(self):
        result = little_endian_to_int(self.version, 4)
        result += encode_variant(len(self.inputs))
        for tx_in in self.inputs:
            result += tx_in.serialize()

        result += encode_variant(len(self.outputs))
        for tx_out in self.outputs:
            result += tx_out.serialize()

        result += int_to_little_endian(self.lock_time, 4)



class TxIn:
    def __int__(self, prev_tx, prev_index, script_sig = None, sequence = 0xffffffff):
        self.prev_tx = prev_tx
        self.prev_index = prev_index
        if script_sig is None:
            self.script_sig = Script()  # 这个东西我们先不考虑它的具体内容
        else:
            self.script_sig = script_sig

        self.sequence =sequence

    def __repr__(self):
        return f"{self.prev_tx.hex()}:{self.prev_index}"

    @classmethod
    def parse(cls, s):
        prev_tx = s.read(32)[::-1] #固定32字节，因为它对应sha256哈希
        prev_index = little_endian_to_int(s.read(4)) #固定4字节
        script_sig = Script.parse(s) #这里我们暂时忽略，因为还不了解Script是什么东西
        sequence = little_endian_to_int(s.read(4)) # 固定4字节
        return cls(prev_tx, prev_index, script_sig, sequence)

    def serialize(self):
        result = self.prev_tx[::-1]
        result += int_to_little_endian(self.prev_index, 4)
        result += self.script_sig.serialize() # 暂时忽略其实现细节
        result += int_to_little_endian(self.sequence, 4)

    def fetch_tx(self, testnet = False ):
        return TxFetch.fetch(self.prev_tx.hex(), testnet = testnet)

    def value(self, testnet = False ):
        tx = self.fetch_tx(testnet = testnet) #本次交易的输入等于上次交易的输出
        return tx.tx_outs[self.prev_index].amount


class TxOut:
    def __init__(self, amount, script_pubkey):
        self.amount = amount
        self.script_pubkey = script_pubkey

    def __repr__(self):
        return f'{self.amout}:{self.script_pubkey}'

    @classmethod
    def parse(cls, s): # s 对应output 二进制流
        amount = little_endian_to_int(s.read(8))
        script_pubkey = Script.parse(s) # 暂时先忽略
        return cls(amount, script_pubkey)

    def serialize(self): # 序列化输出
        result = int_to_little_endian(self.amount, 8)
        result += self.script_pubkey.serialize() # 这里我们先不关心

class TxFetch: #进入给定测试链
    cache = {}

    @classmethod
    def get_url(cls, testnet = False):
        if testnet:
            return 'http://testnet.programmingbitcoin.com'
        else:
            return 'http://mainnet.programmingbitcoin.com'

    @classmethod
    def fetch(cls, tx_id, testnet = False, fresh = False):
        if fresh or (tx_id not in cls.cache):
            url = '{}/tx/{}.hex'.format(cls.get_url(testnet), tx_id)
            response = requests.get(url)
            try:
                raw = bytes.fromhex(response.text.strip())
            except ValueError:
                raise ValueError("not correct response:{}".format(response.text))

            if raw[4] == 0:
                raw = raw[:4] + raw[6:]
                tx = Transation.parse(BytesIO(raw), test_net = testnet)
                tx.lock_time = little_endian_to_int(raw[-4:])
            else:
                tx = Transation.parse(BytesIO(raw), test_net = testnet)
            if tx.id() != tx_id:
                raise ValueError(f"ids are different: {tx.id()} with {tx_id}")
            cls.cache[tx_id] = tx

        cls.cache[tx_id].test_net = testnet
        return cls.cache[tx_id]

