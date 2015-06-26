class Parser:
	def __init__(self, dict_type):
		self.stack = []
		self.current_key = None
		self.root = None
		self._dict_type = dict_type
		self.lineno = 1

	def parse(self, st):
		i = 0
		c = st[i];i+=1
		try:
			while True:
				if c == b'\n':
					self.lineno+=1
					c = st[i];i+=1
					continue
				if c in ' \r\t':
					c = st[i];i+=1
					continue
				elif c in b'{=;}(,)<>':
					self.handlers[c](self, c)
					c = st[i];i+=1
				elif c == b'"':
					start = i
					while True:
						c = st[i];i+=1
						if c == '"':
							break
					self.add_object(st[start:i-1])
					c = st[i];i+=1
				elif b'a'<=c<=b'z' or b'A'<=c<=b'Z' or b'0'<=c<=b'9' or c in b'._-':
					start = i - 1
					while True:
						c = st[i];i+=1
						if b'a'<=c<=b'z' or b'A'<=c<=b'Z' or b'0'<=c<=b'9' or c in b'._':
							pass
						else:
							break
					self.add_object(st[start:i-1])
				else:
					assert 0, "Unexpected character '%s' at %d:\n%s" % (c, i, st[i:i+100])
		except IndexError:
			pass
		assert not self.stack
		return self.root

	def add_object(self, value):
		if not self.stack:
			# this is the root object
			self.root = value
		elif isinstance(self.stack[-1], type([])):
			self.stack[-1].append(value)
		elif isinstance(self.stack[-1], self._dict_type):
			if self.current_key is None:
				self.current_key = value
			else:
				self.stack[-1][self.current_key] = value
				self.current_key = None
		else:
			assert 0

	# element handlers

	def unexpected_token(self, tok):
		return	ValueError("Unexpected character '%s' at line %d" %
				   (tok, self.lineno))

	def begin_dict(self, _):
		d = self._dict_type()
		self.add_object(d)
		self.stack.append(d)

	def end_dict(self, _):
		if self.current_key:
			raise ValueError("missing value for key '%s' at line %d; missing semi-colon?" %
							 (self.current_key,0))
		self.stack.pop()

	def dict_key(self, tok):
		if not self.current_key or not isinstance(self.stack[-1], self._dict_type):
			raise self.unexpected_token(tok)

	def dict_value(self, tok):
		if self.current_key or not isinstance(self.stack[-1], self._dict_type):
			raise self.unexpected_token(tok)

	def begin_array(self, _):
		a = []
		self.add_object(a)
		self.stack.append(a)

	def array_item(self, tok):
		if not isinstance(self.stack[-1], type([])):
			raise self.unexpected_token(tok)

	def end_array(self, _):
		self.stack.pop()

	handlers = {
		'{': begin_dict,
		'=': dict_key,
		';': dict_value,
		'}': end_dict,
		'(': begin_array,
		',': array_item,
		')': end_array,
	}
