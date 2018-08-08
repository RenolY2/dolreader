import struct 
from io import BytesIO, RawIOBase


def read_ubyte(f):
    return struct.unpack("B", f.read(1))[0]

def read_uint32(f):
    return struct.unpack(">I", f.read(4))[0]

def write_uint32(f, val):
    f.write(struct.pack(">I", val))

class DolFile(object):
    def __init__(self, f):
        self._rawdata = BytesIO(f.read())
        f.seek(0)
        fileoffset = 0
        addressoffset = 0x48
        sizeoffset = 0x90 
        
        self._text = []
        self._data = []
        
        nomoretext = False 
        nomoredata = False
        
        self._current_end = None 
        
        # Read text and data section addresses and sizes 
        for i in range(18):
            f.seek(fileoffset+i*4)
            offset = read_uint32(f)
            f.seek(addressoffset+i*4)
            address = read_uint32(f)
            f.seek(sizeoffset+i*4)
            size = read_uint32(f)
            
            if i <= 6:
                if offset == 0:
                    nomoretext = True 
                elif not nomoretext:
                    self._text.append((offset, address, size))
                    # print("text{0}".format(i), hex(offset), hex(address), hex(size))
            else:
                datanum = i - 7
                if offset == 0:
                    nomoredata = True 
                elif not nomoredata:
                    self._data.append((offset, address, size))
                    # print("data{0}".format(datanum), hex(offset), hex(address), hex(size))
        
        f.seek(0xD8)
        self._bssoffset = read_uint32(f)
        self._bsssize = read_uint32(f)
        
        self.bss = BytesIO(self._rawdata.getbuffer()[self._bssoffset:self._bssoffset+self._bsssize])
        
        self._curraddr = self._text[0][1]
        self.seek(self._curraddr)
        
    # Internal function for 
    def _resolve_address(self, gc_addr):
        for offset, address, size in self._text:
            if address <= gc_addr < address+size:
                return offset, address, size 
        for offset, address, size in self._data:
            if address <= gc_addr < address+size:
                return offset, address, size 
        
        raise RuntimeError("Unmapped address: {0}".format(hex(gc_addr)))
    
    # Unsupported: Reading an entire dol file 
    # Assumption: A read should not go beyond the current section 
    def read(self, size):
        if self._curraddr + size >= self._current_end:
            raise RuntimeError("Read goes over current section")
            
        return self._rawdata.read(size)
        self._curraddr += size  
        
    # Assumption: A write should not go beyond the current section 
    def write(self, data):
        if self._curraddr + len(data) >= self._current_end:
            raise RuntimeError("Write goes over current section")
            
        self._rawdata.write(data)
        self._curraddr += len(data)
    
    def seek(self, addr):
        offset, gc_start, gc_size = self._resolve_address(addr)
        self._rawdata.seek(offset + (addr-gc_start))
        
        self._curraddr = addr 
        self._current_end = gc_start + gc_size 
        
    def tell(self):
        return self._curraddr
    
    def save(self, f):
        f.write(self._rawdata.getbuffer())

if __name__ == "__main__":
    # Example usage (reading some enemy info from the Pikmin 2 demo from US demo disc 17)
    
    def read_string(f):
        start = f.tell()
        length = 0
        while f.read(1) != b"\x00":
            length += 1
            if length > 100:
                break
        
        f.seek(start)
        return f.read(length)
    
    entries = []

    with open("main.dol", "rb") as f:
        dol = DolFile(f)

    start = 0x804ac478 # memory address to start of enemy info table.

    for i in range(100):
        dol.seek(start+0x34*i)
        
        # string offset would normally be pointing to a location in RAM and thus
        # wouldn't be suitable as a file offset but because the seek function of DolFile 
        # takes into account the memory address at which the data sections of the dol file 
        # is loaded, we can use the string offset directly..
        stringoffset = read_uint32(dol) 
        identifier = read_ubyte(dol) 
        dol.seek(stringoffset)
        name = read_string(dol)
         
        entries.append((identifier,i, name, hex(stringoffset)))
        
    entries.sort(key=lambda x: x[0])
    for val in entries:
        print(hex(val[0]), val)
    

        
        