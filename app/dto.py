class ProjectFiles:
    def __init__(self, project):
        self.coords_list = project.coords()
        self.logs_list = project.logs()
        self.core_list = project.core()
