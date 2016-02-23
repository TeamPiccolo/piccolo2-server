import piccolo

if __name__ == '__main__':
    
    pd = piccolo.PiccoloDispatcher()
    pd.registerComponent('piccolo',piccolo.Piccolo())
    print pd.getComponentList()
    print pd._execute('piccolo','ping')

    pc = piccolo.PiccoloController()

    pd.registerController(pc)

    pc.taskQ.put(('components',None,{}))
    pc.taskQ.put(('piccolo','ping',{}))
    pc.taskQ.put(('stop',None,{}))

    pd.run()

    print
    print 'processing queue'
    while True:
        d = pc.doneQ.get()
        print d
        if d=='stopped':
            break
        
