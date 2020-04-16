'''Plot Module Interdependency Structure


Current Issues / Limitations:
    + cant seem to find a way to find whether ast.Name nodes are functions or normal variables

Some of this code is influenced by / shamelessly copied off of:
    + csl @ https://stackoverflow.com/a/31005891/6794367
    + Andriy Ivaneyko @ https://stackoverflow.com/a/56456272/6794367

'''
import ast, sys, os, types
import base64

def fillGraph(graph, rootDir, ignore = []):
    for item in os.listdir(rootDir):
        if os.path.isdir(os.path.join(rootDir,item)):
            # print('dir:',item)
            fillGraph(graph, os.path.join(rootDir,item))
            # print(os.path.join(rootDir,item))
        elif os.path.isfile(os.path.join(rootDir,item)):
            if item.endswith('.py'):
                graph['nodes'][item[:-3]] = { # <-- [:-3] removes '.py' from filename
                    'path': os.path.join(rootDir,item),
                    'nodes': [],
                    'dependencies': [],
                }

def fillGraph_Github(graph, repo, location = '', ignore = []):
    for i, item in enumerate(repo.get_contents(location)):

        if item.type == 'file':

            if item.name.endswith('.py'):
                graph['nodes'][item.name[:-3]] = { # <-- [:-3] removes '.py' from filename
                    'path': os.path.join(location,item.name),
                    'nodes': [],
                    'dependencies': [],
                }
        elif item.type == 'dir':
            fillGraph_Github(graph, repo, location = os.path.join(location,item.name))


def fillConnections(graph, github_repo = None):
    for x in graph['nodes'].keys():
        # print(x)
        if github_repo != None:
            module_tree = ast.parse(base64.b64decode(github_repo.get_contents(graph['nodes'][x]['path']).content), filename=graph['nodes'][x]['path']) # <-- from csl @ https://stackoverflow.com/a/31005891/6794367
        else:
            with open(graph['nodes'][x]['path'], "rt") as file:
                module_tree = ast.parse(file.read(), filename=graph['nodes'][x]['path']) # <-- from csl @ https://stackoverflow.com/a/31005891/6794367
            
        for branch in module_tree.body:
            
            ## get defined functions
            if isinstance(branch,ast.FunctionDef):
                graph['nodes'][x]['nodes'].append({'id': branch.name, 'type':'defFunc'})
            
            ## get imported modules
            elif isinstance(branch, ast.Import) or isinstance(branch, ast.Import):
                for imp in branch.names:
                    if imp.name in graph['nodes'].keys():
                        graph['nodes'][x]['dependencies'].append({'id': imp.name, 'type':'intDep'})
                    else:
                        graph['nodes'][x]['dependencies'].append({'id': imp.name, 'type':'extDep'})

            ## get variable assignments
            elif isinstance(branch,ast.Assign):

                ## check if a lambda function
                if isinstance(branch.value,ast.Lambda): # <-- from Andriy Ivaneyko @ https://stackoverflow.com/a/56456272/6794367
                    for target in branch.targets:
                        graph['nodes'][x]['nodes'].append({'id': target.id, 'type':'lambdaFunc'})
                else:
                    for target in branch.targets:
                        if isinstance(target, ast.Subscript) == False:
                            try:
                                graph['nodes'][x]['nodes'].append({'id': target.id, 'type':'unknownObjAssign'})
                            except Exception as e:
                                print('\n--------- EXCEPTION --------\n')
                                print(target)
                                print(dir(target))
                                print('\n***\n',e)
                                print('\n\n- - - - - - - - - - - - - - - - - - - ')
                                print('- - - - - - - - - - - - - - - - - - -\n\n')


def get_repo(rootDir, from_github = False, authentication = []):
    graph = {
        'nodes': {},
        'root': rootDir
    }

    if from_github == False:
        fillGraph(graph, graph['root'])
        fillConnections(graph)

    else:
        try: from github import Github 
        except: print('failed to load PyGithub module (if you haven\'t downloaded it, that might fix this bug); exiting...'); exit()
        repo = Github(*authentication).get_repo(rootDir)
        fillGraph_Github(graph, repo, location = '')
        fillConnections(graph, github_repo = repo)


    return graph


def plot_dependencies(graph, filename, style = 'shell'):
    import matplotlib.pyplot as plt 
    import networkx as nx 
    
    fig = plt.figure(figsize = [20,10])

    positions = {
        'random': lambda G: nx.layout.random_layout(G),
        'circular': lambda G: nx.layout.circular_layout(G),
        'planar': lambda G: nx.layout.planar_layout(G),
        'kamada_kawai': lambda G: nx.layout.kamada_kawai_layout(G),
        'spring': lambda G: nx.layout.spring_layout(G),
        'shell': lambda G: nx.layout.shell_layout(G),
        'spectral': lambda G: nx.layout.spectral_layout(G),
        'spiral': lambda G: nx.layout.spiral_layout(G),
    }

    G = nx.DiGraph()

    for node in graph['nodes']:
        G.add_node(node)
        for connection in graph['nodes'][node]['dependencies']:
            # if connection['type'] != 'extDep':
                if connection['id'] not in graph['nodes']:
                    G.add_node(connection['id'].split('.')[0])
                G.add_edge(*[node, connection['id'].split('.')[0]])

    pos = positions[style](G)
    
    nx.draw(
        G, 
        pos, 
        with_labels = True, 
        font_weight = 'bold',
        arrows = True,
        font_color = [0,0,0,.75],
        node_color = [[.75,.75,.75,1]],
        node_size = 5000,
        width = 3,
        arrowsize = 20,
        edgecolors = [[0,0,0,.1]],
        edge_color = [[.3,.3,.3,.5]],
        linewidths = 4,
        # ax = ax,
    )

    plt.savefig(filename)


if __name__ == "__main__":
    import pickle
    graph = get_repo('mwetzel7r/python-module-grapher', from_github = True) # <-- from_github defaults to False; i.e., it assumes you're plotting a local repo unless you tell it otherwise

    # ##__save graph for later use (to avoid frequent calls to the github API)
    # with open('savedgraph.pckl','wb') as file:
        # pickle.dump(graph, file)

    # ##__load previous graph
    # with open('savedgraph.pckl', 'rb') as file:
        # graph = pickle.load(file)

    plot_dependencies(graph, 'results.png', style = 'kamada_kawai')

