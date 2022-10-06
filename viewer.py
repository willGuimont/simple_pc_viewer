import platform

import OpenGL.GL as gl
import glfw
import glm
import numpy as np

SCREEN_WIDTH = 256 * 3
SCREEN_HEIGHT = 256 * 3

AZIMUTH = 0
ALTITUDE = np.pi / 6
DISTANCE = 0.5

MODEL_MAT_UNIFORM = 'modelMat'
VIEW_MAT_UNIFORM = 'viewMat'
PROJ_MAT_UNIFORM = 'projMat'
POINT_SIZE = 'pointSize'


def create_window(title):
    # initialize the library
    if not glfw.init():
        return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    if platform.system() == 'Darwin':
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)

    # create a windowed mode window and its OpenGL context
    window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, title, None, None)
    if not window:
        glfw.terminate()
        return
    glfw.make_context_current(window)

    def framebuffer_size_callback(_, width, height):
        global SCREEN_WIDTH, SCREEN_HEIGHT
        SCREEN_WIDTH = width
        SCREEN_HEIGHT = height
        gl.glViewport(0, 0, width, height)

    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)

    def key_callback(_, key, scancode, action, mods):
        global AZIMUTH, ALTITUDE, DISTANCE
        d_angle = 0.01
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_A:
            AZIMUTH -= d_angle
        elif key == glfw.KEY_D:
            AZIMUTH += d_angle
        elif key == glfw.KEY_S:
            ALTITUDE += d_angle
        elif key == glfw.KEY_W:
            ALTITUDE -= d_angle
        elif key == glfw.KEY_Q:
            DISTANCE += 0.01
        elif key == glfw.KEY_E:
            DISTANCE -= 0.01

    glfw.set_key_callback(window, key_callback)
    return window


def setup_shaders():
    # vertex shaders
    vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
    with open('shaders/vertex.vert') as f:
        vertex_shader_source = f.read()
    gl.glShaderSource(vertex_shader, vertex_shader_source)
    gl.glCompileShader(vertex_shader)
    if not gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS):
        print(gl.glGetShaderInfoLog(vertex_shader))

    # fragment shader
    fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
    with open('shaders/fragment.frag') as f:
        fragment_shader_source = f.read()
    gl.glShaderSource(fragment_shader, fragment_shader_source)
    gl.glCompileShader(fragment_shader)
    if not gl.glGetShaderiv(fragment_shader, gl.GL_COMPILE_STATUS):
        print(gl.glGetShaderInfoLog(fragment_shader))

    # link shader
    shader_program = gl.glCreateProgram()
    gl.glAttachShader(shader_program, vertex_shader)
    gl.glAttachShader(shader_program, fragment_shader)
    gl.glLinkProgram(shader_program)
    if not gl.glGetProgramiv(shader_program, gl.GL_LINK_STATUS):
        print(gl.glGetProgramInfoLog(shader_program))
    gl.glDeleteShader(vertex_shader)
    gl.glDeleteShader(fragment_shader)

    gl.glEnable(gl.GL_PROGRAM_POINT_SIZE)
    model_mat_location = gl.glGetUniformLocation(shader_program, MODEL_MAT_UNIFORM)
    view_mat_location = gl.glGetUniformLocation(shader_program, VIEW_MAT_UNIFORM)
    proj_mat_location = gl.glGetUniformLocation(shader_program, PROJ_MAT_UNIFORM)
    point_size_location = gl.glGetUniformLocation(shader_program, POINT_SIZE)

    return shader_program, [vertex_shader, fragment_shader], {
        MODEL_MAT_UNIFORM: model_mat_location,
        VIEW_MAT_UNIFORM: view_mat_location,
        PROJ_MAT_UNIFORM: proj_mat_location,
        POINT_SIZE: point_size_location
    }


def setup_vertices(point_cloud: np.ndarray):
    vertices = point_cloud.astype(np.float32)
    max_dist = np.max(np.linalg.norm(vertices, axis=1))
    vertices[:, :3] /= max_dist

    vao = gl.glGenVertexArrays(1)
    vbo = gl.glGenBuffers(1)
    ebo = gl.glGenBuffers(1)

    gl.glBindVertexArray(vao)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices, gl.GL_STATIC_DRAW)

    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
    indices = np.arange(vertices.shape[0])
    gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices, gl.GL_STATIC_DRAW)

    # position
    gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, gl.GL_FALSE, 0 * vertices.itemsize, None)
    gl.glEnableVertexAttribArray(0)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glBindVertexArray(0)

    return vao, vbo, ebo


def show_point_cloud(point_cloud: np.ndarray):
    window = create_window('Render')
    shader_program, shaders, uniforms = setup_shaders()
    vao, vbo, ebo = setup_vertices(point_cloud)

    # loop until the user closes the window
    while not glfw.window_should_close(window):
        # matrices
        global AZIMUTH, ALTITUDE, DISTANCE
        eye = glm.vec3(
            DISTANCE * np.cos(AZIMUTH) * np.sin(ALTITUDE),
            DISTANCE * np.sin(AZIMUTH) * np.sin(ALTITUDE),
            DISTANCE * np.cos(ALTITUDE)
        )
        center = glm.vec3(0, 0, 0)
        up = glm.vec3(0, 0, -1)

        proj_mat = glm.perspective(30, SCREEN_WIDTH / SCREEN_HEIGHT, 0.01, 100)
        view_mat = glm.lookAt(eye, center, up)
        model_mat = glm.translate(glm.identity(glm.fmat4), glm.vec3(0, 0, 0))

        # rendering
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glUseProgram(shader_program)

        gl.glUniformMatrix4fv(uniforms[PROJ_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(proj_mat))
        gl.glUniformMatrix4fv(uniforms[VIEW_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(view_mat))
        gl.glUniformMatrix4fv(uniforms[MODEL_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(model_mat))
        gl.glUniform1f(uniforms[POINT_SIZE], 2.5)

        gl.glBindVertexArray(vao)
        gl.glDrawElements(gl.GL_POINTS, point_cloud.shape[0], gl.GL_UNSIGNED_INT, None)
        gl.glBindVertexArray(0)

        # shader logs
        for i, shader in enumerate(shaders):
            shader_log = gl.glGetShaderInfoLog(shader)
            if shader_log != '':
                print('vertex' if shader == 1 else 'fragment')
                print(shader_log)

        glfw.swap_buffers(window)
        glfw.poll_events()

        # gl.glReadBuffer(gl.GL_FRONT)
        # pixels = gl.glReadPixels(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, gl.GL_RGBA, gl.GL_FLOAT)
        # img = np.frombuffer(pixels, np.float32)
        # img = img.reshape((SCREEN_WIDTH, SCREEN_HEIGHT, -1))
        # img = img[::-1, :]
        # img = Image.fromarray(np.uint8(img * 255)).convert('RGB')

    # cleanup
    gl.glDeleteVertexArrays(1, vao)
    gl.glDeleteBuffers(1, vbo)
    gl.glDeleteBuffers(1, ebo)
    gl.glDeleteProgram(shader_program)

    glfw.terminate()


if __name__ == "__main__":
    import pickle

    with open('data/pc.pkl', 'rb') as f:
        pc = pickle.load(f)

    show_point_cloud(pc[::10])
