import piccolo

if __name__ == '__main__':
    
    pd = piccolo.PiccoloDispatcher()
    pd.registerComponent('piccolo',piccolo.Piccolo())
    print pd.getComponentList()
    print pd._execute('piccolo','ping')

    pc = piccolo.PiccoloController()

    pd.registerController(pc)

    pd.start()

    print pc.call('components')
    print pc.call('ping','piccol')
    print pc.call('pin','piccolo')
    print pc.call('ping','piccolo')

    pc.call('stop')

