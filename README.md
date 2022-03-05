在区块链应用中，最重要的就是所谓的交易。通俗来说，交易就是把比特币或某种数字货币从一个人转手给另一个人。从数据结构上看，交易包含4个成分，分别为版本，输入，输出，锁定时间。版本用于决定该交易能够使用什么样的附加功能，输入是一个复杂概念，在后面解释。，输出对应接收者，锁定时间对应交易的有效期。

我们先从代码上对交易进行定义：
```
from EllipticCurves import hash256
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
```

上面代码只定义了交易对应的4个字段，同时有一个函数还没有实现，那就是serialize(),它的作用是把Transation类的实例进行序列化，后面我们在处理它。我们先深入看各个字段的含义。  version字段用来表示当前交易可以支持那种功能。例如windows操作系统就有不同的版本，对应版本又有不同功能或者API，知道操作系统的版本，我们就能知道系统是否具备特定的功能或者接口可以调用，交易的版本也处于类似目的。通常情况下交易的版本号都是1，在某些特定情形下会是2.

从代码上看，inputs是一个数组，其中包含多个元素。其中每个元素类似指针，指向了上一次交易的输出。如果输出表示我们把数字货币支付给别人，那么首先我们要从被人那里或某个地方获得对应货币，毕竟你要先有钱才能去花钱。对于比特币应用而言，每个输入都要对应两个要点，首先要指明你以前接收到的货币，第二，证明这些货币确实属于你。第二部分对应上一节描述的ECDSA，也就是我们要用自己的私钥产生数字签名以便证明我们拥有对应货币。

之所以输入字段要对应数组，那是应为一定货币数值可能会通过多次支付花出。例如你有一百块，你可能用20买早餐，20买午餐，60买晚餐，这样就对应3个输入，或者你一顿吃了一百块，那么就对应一个输入。

从二进制数据上看，跟在版本字段后面的输入字段要分多部分来解读。版本字段固定是1个字节，然后跟着可变个字节用来表示输入的数量。为了节省空间，跟在版本字段后面用于表示输入数量的信息遵循如下解读规则：
1，如果输入数量少于253，那么使用一个字节来表示
2，如果输入的数量在253 和 2^16-1之间，也就是输入数量能用2个字节就能表示。那么跟着版本字段后面是数值253，它占据一个字节，接下来用两个字节来表示输入的数量。
3，如果输入的数量在2^16 到2 ^32 -1 之间，也就是输入的数量需要4个字节表示。那么在版本字段后面先跟着数值254，然后用4个字节来表示输入的数量
3，如果输入的数量在2^32  到 2 ^ 64 - 1之间，也就是输入的数量需要用8个字节表示，那么在版本字段你后面先跟着数值255，然后用8个字节表示输入数量。

通过具体代码才能更好理解上面在说什么：
```
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
```
通过上面代码，或许我们能对前面描述的编码规则有更好理解。知道输入的数量后，我们就可以解析输入的数据结构。输入包含4部分分别为：上一次交易的ID，上一次交易的索引，ScriptSig, Squence，后面两个不好用中文翻译，后面我们用代码来解释他们。上一次交易ID其实就是对上一次交易数据进行二进制序列化后计算hash256的结果。因此这个字段长度就固定为32字节，同时上一次交易索引用4字节表示，他们都使用小端编码。

ScriptSig涉及到比特币只能合约的脚步语言。这是一个可变长度的字段，sequence是一个固定4字节的字段。sequence 和 lock_time这两个字段原来是中本聪用来实现“高频交易”，它的意思是，如果小明给小花支付x个比特币作为报酬，后来因为小明帮了小花一个忙，于是小花要支付给小明y个比特币作为报酬，如果x>y，那么小明直接支付给小花x-y个比特币就可以，不需要让小明先支付给小花x个比特币，然后小花再支付给小明y个比特币，也就是中本聪希望能将多次交易综合起来形成一次交易，只不过这个想法存在严重的漏洞，因此没能使用在比特币中。

我们看看交易输入如何在代码上定义：
```
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
```
上面代码中我们有一个尚未了解的Script对象，我们假设它已经存在的情况下，我们就能给出输入的解析逻辑代码，有了输入解析后，交易的解析也就能实现：
```
class Transation:
    @classmethod
    def parse(cls, s, testnet = False):
        version = little_endian_to_int(s.read(4))
        num_inputs = read_variant(s)
        inputs = []
        for _ in range(num_inputs):
            inputs.append(TxIn.parse(s))
        return cls(version, inputs, None, None, testnet = testnet)
```
接着我们看看输出字段，输出表示谁将获得本次交易的比特币。输出也是多个对象，因为一次交易可能需要支付给多方，输出对象有两个字段，分别为amount和ScriptPubKey，amount就是要支付的比特币数量，它的单位是1/100,000,000个比特币，该字段占据8个字节。

ScriptPubKey同样与比特币的智能合约脚本有关。它可以看做一个ATM机的钥匙，所有人都能往里面存钱，只有有钥匙的人才能打开取钱。这个字段的意义需要在后面章节才能理解,它也是一个可变长字段，我们需要先解析若干个字节获得它的具体长度，然后才能得到它的二进制内容，我们先从代码上对其进行简单的定义，让这个概念变得具体一些：
```

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
```
现在我们顺便也加上在交易对象里对输出的解析:
```
Transation:
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
        return cls(version, inputs, outputs, None, testnet = testnet)
```
接下来自然就是对lock_time字段的解析。这个字段根据其值有两种不同解读，如果它的值小于500,000,000，那么它表示公链中的区块数，例如lock_time=600,000,它表示交易必须要等到公链中出现第600,001个区块后才生效，如果大于500,000,000，那么它表示unix时间戳。这里需要注意的是，如果所有输入对象里面的sequence都取值为ffffffff时，它会被忽略，由于它对应4个字节，因此在交易对象的解析中，把二进制流最后4字节读取出来即可：
```
Transation:
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
```
下面我们看看输入和输出的序列化操作，他们是前面我们描述的解析操作的逆操作：
```
class TxOut:
    def serialize(self):
            def serialize(self): # 序列化输出
	        result = int_to_little_endian(self.amount, 8)
	        result += self.script_pubkey.serialize() # 这里我们先不关心

class TxIn:
        def serialize(self):
        result = self.prev_tx[::-1]
        result += int_to_little_endian(self.prev_index, 4)
        result += self.script_sig.serialize() # 暂时忽略其实现细节
        result += int_to_little_endian(self.sequence, 4)

class Transation:
        def serialize(self):
        result = little_endian_to_int(self.version, 4)
        result += encode_variant(len(self.inputs))
        for tx_in in self.inputs:
            result += tx_in.serialize()

        result += encode_variant(len(self.outputs))
        for tx_out in self.outputs:
            result += tx_out.serialize()

        result += int_to_little_endian(self.lock_time, 4) 
```

对于一个交易而言，输入收入，输出对应支付，比特币规定输入必须大于等于输出，多出来的这部分作为矿工的奖励或报酬。输入与输出的差额也叫做交易费用，但问题在于我们上面的代码定义中，只有输出有amount，输入没有，因此我们需要到公链里面去查找输入对应的amount，不过我们不需要进入公链，因为有很多比特币的模拟链，也就是有人自己开发了一个类似比特币的区块链，这些链主要用于测试，因此也叫比特币的测试链，我们看看如何进入给定的测试链：
```
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
```
上面的代码还跑不了，因为我们还有Script对象没有实现。另外模拟一个以太坊区块链其实没有那么复杂，市面上有大量的测试链，以后有时间了我们也自己实现一个。有了测试链后，我们可以让输入对象从测试链读取交易的输入额度：
```
class TxIn:
     def fetch_tx(self, testnet = False ):
        return TxFetch.fetch(self.prev_tx.hex(), testnet = testnet)

    def value(self, testnet = False ):
        tx = self.fetch_tx(testnet = testnet) #本次交易的输入等于上次交易的输出
        return tx.tx_outs[self.prev_index].amo`在这里插入代码片`unt
```

当前代码还跑不了，但是通过代码我们可以比较好的了解相应概念，下一节我们处理Script对象后就能让现在代码跑起来。

