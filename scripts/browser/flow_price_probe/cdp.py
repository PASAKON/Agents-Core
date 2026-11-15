import sys, socket, os, base64, json, struct, urllib.request, time
sys.stdout.reconfigure(encoding="utf-8")
def tabs(): return json.load(urllib.request.urlopen("http://127.0.0.1:9226/json/list", timeout=8))
class Tab:
    def __init__(self, tid_prefix):
        t=[x for x in tabs() if x["id"].startswith(tid_prefix) and x["type"]=="page"][0]
        ws=t["webSocketDebuggerUrl"]; host,rest=ws[5:].split("/",1); h,p=host.split(":")
        self.s=socket.create_connection((h,int(p)),timeout=20)
        key=base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf=b""
        while b"\r\n\r\n" not in buf: buf+=self.s.recv(4096)
        self.i=0
    def _send(self,obj):
        d=json.dumps(obj).encode(); m=os.urandom(4); n=len(d); h=bytes([0x81])
        h+= bytes([0x80|n]) if n<126 else bytes([0x80|126])+struct.pack(">H",n) if n<65536 else bytes([0x80|127])+struct.pack(">Q",n)
        self.s.sendall(h+m+bytes(b^m[i%4] for i,b in enumerate(d)))
    def _rd(self,n):
        b=b""
        while len(b)<n:
            c=self.s.recv(n-len(b))
            if not c: raise EOFError
            b+=c
        return b
    def _recv(self):
        msg=b""
        while True:
            b1,b2=self._rd(2); n=b2&0x7F
            if n==126: n=struct.unpack(">H",self._rd(2))[0]
            elif n==127: n=struct.unpack(">Q",self._rd(8))[0]
            msg+=self._rd(n)
            if b1&0x80: return json.loads(msg.decode("utf-8","replace"))
    def call(self,method,**params):
        self.i+=1; i=self.i; self._send({"id":i,"method":method,"params":params}); t0=time.time()
        while time.time()-t0<25:
            r=self._recv()
            if r.get("id")==i: return r
    def ev(self,expr):
        r=self.call("Runtime.evaluate",expression=expr,returnByValue=True,awaitPromise=True)
        return r.get("result",{}).get("result",{}).get("value")
