# PATTERN: OOP-CBV-01 — class-based view dispatch
class View:
    def dispatch_request(self): return self.get()
    def get(self): pass
View().dispatch_request()
