# PATTERN: CORE-PROC-01
# PATTERN: REF-EXCEPTION-01 — exception reference
try: run()
except Exception as err: handle(err)
# PATTERN: CALL-PROMISE-01 — async await chain
async def index(): await decode()
async def decode(): pass
def run(): pass
def handle(e): pass
