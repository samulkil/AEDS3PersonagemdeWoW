from controller.HashExtensivel import HashExtensivel
h = HashExtensivel('dados/index_contas_usuario')
print('Search samuel:', h.search('samuel'))
print('Hash of samuel:', abs(hash('samuel')) % (2**31))