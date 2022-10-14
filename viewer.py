import ctypes
import platform
from typing import Optional, Dict, List

import OpenGL.GL as gl
import glfw
import glm
import numpy as np

PROJ_MAT_UNIFORM = 'vertProjMat'
VIEW_MAT_UNIFORM = 'vertViewMat'
MODEL_MAT_UNIFORM = 'vertModelMat'
POINT_SIZE = 'vertPointSize'
RENDER_MODE = 'vertRenderMode'


def create_window(title, screen_width, screen_height):
    # initialize the library
    if not glfw.init():
        return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    if platform.system() == 'Darwin':
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)

    # create a windowed mode window and its OpenGL context
    window = glfw.create_window(screen_width, screen_height, title, None, None)
    if not window:
        glfw.terminate()
        return
    glfw.make_context_current(window)

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
    render_mode_location = gl.glGetUniformLocation(shader_program, RENDER_MODE)

    return shader_program, [vertex_shader, fragment_shader], {
        MODEL_MAT_UNIFORM: model_mat_location,
        VIEW_MAT_UNIFORM: view_mat_location,
        PROJ_MAT_UNIFORM: proj_mat_location,
        POINT_SIZE: point_size_location,
        RENDER_MODE: render_mode_location,
    }


def setup_buffers(point_cloud, labels, color_map):
    has_labels = labels is not None

    size_per_point = 4
    if has_labels:
        size_per_point += 3

    vertices = np.zeros((point_cloud.shape[0], size_per_point), dtype=np.float32)

    vertices[:, :4] = point_cloud
    if has_labels:
        for label, color in color_map.items():
            vertices[labels == label, 4:7] = np.array(color[::-1]) / 255

    max_dist = np.max(np.linalg.norm(vertices[:, :3], axis=1))
    vertices[:, :3] /= max_dist

    vao = gl.glGenVertexArrays(1)
    vbo = gl.glGenBuffers(1)
    ebo = gl.glGenBuffers(1)

    gl.glBindVertexArray(vao)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.size * vertices.itemsize, vertices.flatten(), gl.GL_STATIC_DRAW)

    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
    indices = np.arange(vertices.shape[0], dtype=np.uintc)
    gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.size * indices.itemsize, indices.flatten(), gl.GL_STATIC_DRAW)

    # position
    gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, gl.GL_FALSE, size_per_point * vertices.itemsize, None)
    gl.glEnableVertexAttribArray(0)

    if has_labels:
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, size_per_point * vertices.itemsize,
                                 ctypes.c_void_p(4 * vertices.itemsize))
        gl.glEnableVertexAttribArray(1)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glBindVertexArray(0)

    return vao, vbo, ebo


def show_point_cloud(win_title: str,
                     point_cloud: np.ndarray,
                     label: Optional[np.ndarray] = None,
                     color_map: Dict[int, List[int]] = None,
                     screen_width: int = 256 * 3,
                     screen_height: int = 256 * 3,
                     azimuth: float = -np.pi / 2,
                     altitude: float = 1e-3,
                     distance: float = 0.5,
                     x: float = 0,
                     y: float = 0,
                     z: float = 0):
    """
    Opens an OpenGL window to display a point cloud
    :param win_title: title of the window
    :param point_cloud: point cloud to display (N, 4)
    :param label: semantic label for each point (N,)
    :param color_map: maps each semantic label to a color (BGR, 0-255)
    :param screen_width: screen width
    :param screen_height: screen height
    :param azimuth: angle around the z-axis
    :param altitude: angle from the z-axis
    :param distance: distance of the camera from the origin
    :param x: translates the pc in x
    :param y: translates the pc in y
    :param z: translates the pc in z
    :return: None
    """
    if label is not None and color_map is None:
        raise ValueError('Need to provide colod_map')

    # normalize and change sign of translation
    max_dist = np.max(np.linalg.norm(point_cloud[:, :3], axis=1))
    x /= max_dist
    y /= max_dist
    z /= max_dist

    window = create_window(win_title, screen_width, screen_height)
    shader_program, shaders, uniforms = setup_shaders()
    vao, vbo, ebo = setup_buffers(point_cloud, label, color_map)
    render_mode = 0
    render_mode_dict = {0: 0, 1: 0.1, 2: 0.2}

    def framebuffer_size_callback(_, width, height):
        nonlocal screen_width, screen_height
        screen_width = width
        screen_height = height
        gl.glViewport(0, 0, screen_width, screen_height)

    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)

    def key_callback(_, key, scancode, action, mods):
        nonlocal azimuth, altitude, distance, x, y, z, render_mode
        d_angle = 0.01
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_A:
            azimuth -= d_angle
        elif key == glfw.KEY_D:
            azimuth += d_angle
        elif key == glfw.KEY_S:
            altitude += d_angle
        elif key == glfw.KEY_W:
            altitude -= d_angle
        elif key == glfw.KEY_E:
            distance += 0.01
        elif key == glfw.KEY_Q:
            distance -= 0.01
        elif key == glfw.KEY_UP:
            x += 0.01
        elif key == glfw.KEY_DOWN:
            x -= 0.01
        elif key == glfw.KEY_LEFT:
            y += 0.01
        elif key == glfw.KEY_RIGHT:
            y -= 0.01
        elif key == glfw.KEY_Z:
            z += 0.01
        elif key == glfw.KEY_X:
            z -= 0.01
        elif action == glfw.PRESS and key == glfw.KEY_SPACE:
            render_mode = (render_mode + 1) % len(render_mode_dict)

    glfw.set_key_callback(window, key_callback)

    # loop until the user closes the window
    while not glfw.window_should_close(window):
        # matrices
        eye = glm.vec3(
            distance * np.cos(azimuth) * np.sin(altitude),
            distance * np.sin(azimuth) * np.sin(altitude),
            distance * np.cos(altitude)
        )
        center = glm.vec3(0, 0, 0)
        up = glm.vec3(0, 0, -1)

        proj_mat = glm.perspective(30, screen_width / screen_height, 1e-6, 1e6)
        view_mat = glm.lookAt(eye, center, up)
        model_mat = glm.translate(glm.identity(glm.fmat4), glm.vec3(x, y, z))

        # rendering
        gl.glClearColor(0.75, 0.75, 0.75, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glUseProgram(shader_program)

        gl.glUniformMatrix4fv(uniforms[PROJ_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(proj_mat))
        gl.glUniformMatrix4fv(uniforms[VIEW_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(view_mat))
        gl.glUniformMatrix4fv(uniforms[MODEL_MAT_UNIFORM], 1, gl.GL_FALSE, glm.value_ptr(model_mat))
        gl.glUniform1f(uniforms[POINT_SIZE], 2.5)
        gl.glUniform1f(uniforms[RENDER_MODE], render_mode_dict[render_mode])

        gl.glBindVertexArray(vao)
        gl.glDrawElements(gl.GL_POINTS, point_cloud.shape[0], gl.GL_UNSIGNED_INT, None)
        gl.glBindVertexArray(0)

        # shader logs
        for i, shader in enumerate(shaders):
            shader_log = gl.glGetShaderInfoLog(shader)
            if shader_log != '':
                print('vertex' if shader == 1 else 'fragment')
                print(shader_log)
        if (err := gl.glGetError()) != 0:
            print(f'error {err}')

        glfw.swap_buffers(window)
        glfw.poll_events()

    # cleanup
    gl.glDeleteVertexArrays(1, vao)
    gl.glDeleteBuffers(1, vbo)
    gl.glDeleteBuffers(1, ebo)
    gl.glDeleteProgram(shader_program)

    glfw.terminate()


def print_controls():
    print("""
    wasd to rotate
    qe to move closer/farther
    arrow keys to move around in xy plane
    zx to move up and down
    space to toggle intensity-label-solid
    """)


if __name__ == "__main__":
    import pickle
    import yaml

    with open('data/pc.pkl', 'rb') as f:
        pc = pickle.load(f)
    with open('data/labels.pkl', 'rb') as f:
        labels = pickle.load(f)
    with open('data/color_map.yaml', 'r') as f:
        color_map = yaml.safe_load(f)['color_map']

    decimate = 10
    show_point_cloud('Render', pc[::decimate], labels[::decimate], color_map)
