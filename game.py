import math
import pygame

import pymunk
import pymunk.pygame_util
from pymunk.vec2d import Vec2d

pygame.init()
screen = pygame.display.set_mode((1200, 600))
clock = pygame.time.Clock()
running = True
space = pymunk.Space()
pixel_scale = 20.0 # pixels per metre
space.gravity = (0.0, -9.8)
pymunk.pygame_util.positive_y_is_up = True
draw_options = pymunk.pygame_util.DrawOptions(screen)
font_height = 30
myfont = pygame.font.SysFont('Arial', font_height)
image_pixel_scale = 63.0 # there are about 63 pixels per metre in the pictures I have
image_scale = pixel_scale / image_pixel_scale

pilotImg = pygame.image.load('pilot.png')
wingImg = pygame.image.load('wing.png')

pilotImg = pygame.transform.scale(pilotImg, (int(pilotImg.get_width()*image_scale), int(pilotImg.get_height()*image_scale)))
wingImg = pygame.transform.scale(wingImg, (int(wingImg.get_width()*image_scale), int(wingImg.get_height()*image_scale)))

pilot_centre = Vec2d(49,64) * image_scale
thrust = False
thrust_on_wing = False
wing_centre = Vec2d(93,56) * image_scale

w = screen.get_width()
h = screen.get_height()
draw_forces = False
force_draw_factor = 0.003
background_spacing = 10 # metres
camera = None
text_y = 0
winch_length = 10.0 # used if winch
winch = False
winch_does_up_down = True
start_frame = 106
line_wave_time = start_frame
fast_forward = 1

sim_mode = 'gliding'
sim_mode = 'flapping'

if sim_mode == 'gliding':
    start_height = 20
    line_wave = False
    brake_angle = 0.2
    start_v = (-7,0.0)
    lines_use_slide_joints = True
    pilot_runs = False
else: # flapping
    start_height = 0.3
    line_wave = True
    line_wave_cycle_length = 251
    brake_angle = 0.2
    start_v = (-11,0.0)
    lines_use_slide_joints = False
    pilot_runs = True


class Graph:
    def __init__(self, pts):
        # make sure pts is a list of (x,y) points always increasing in x
        self.pts = pts
        
    def get_y_at_x(self, x):
        y = None
        prev_p = None
        for pt in self.pts:
            y = pt[1]
            if x < pt[0]:
                if prev_p:
                    y = prev_p[1] + (x-prev_p[0])/(pt[0]-prev_p[0])*(pt[1]-prev_p[1])
                break
            prev_p = pt
        return y
    
class GameBody():
    def __init__(self, pos, v, mass, poly_pts):
        self.body = pymunk.Body()
        self.body.position = pos
        self.body.velocity = v
        self.shape = pymunk.Poly(self.body, poly_pts)
        self.shape.mass = mass
        self.shape.friction = 0.7
        space.add(self.body, self.shape)

    def draw_vector(self, pos, v, colour = (0,0,0)):
        wpos = self.body.local_to_world(Vec2d(pos[0], pos[1]))
        pygame.draw.line(screen, colour, world_to_screen(wpos), world_to_screen(wpos + v * force_draw_factor))

    def apply_parasitic_drag(self, coefficient):
        v, v_magn = self.body.velocity.normalized_and_length()
        drag = 1.0 * v_magn * v_magn * coefficient
        world_pos = self.body.local_to_world((0,0))
        self.body.apply_force_at_world_point(-v * drag, world_pos)
        
    def draw_shape(self):
        s = None
        prev = None
        for v in self.shape.get_vertices():
            x,y = v.rotated(self.shape.body.angle) + self.shape.body.position
            if s == None:
                s = (x,y)
            else:
                p = (x,y)
                if prev != None:
                    draw_line(prev, p)
                prev = (x,y)
        if prev != None:
            draw_line(prev, s)

class Wing(GameBody):
    def __init__(self, alt):
        poly_pts = [(0.635, -2.667),(-0.048, -2.556),(-0.841, -1.619),(-1.317, 0.698),(-0.984, 0.841),(1.349, 0.254),(1.016, -1.381)]
        GameBody.__init__(self, (0,alt),start_v, 4, poly_pts)
        self.body.angle = 0.3
        self.airflow = Vec2d(0,0)
        self.lift = Vec2d(0,0)
        self.drag = Vec2d(0,0)
        self.pressure_pos = 0
        self.lift_coefficients = Graph([(-100, 0), (-30, -0.5), (-10, -0.5), (-8, -0.4), (-6, -0.2), (-4, 0), (-2, 0.2), (0, 0.42), (2, 0.66), (4, 0.82), (6, 1.1), (8, 1.2), (10, 1.4), (12, 1.45), (14, 1.52), (16, 1.5), (18, 1.45), (30, 1.4), (100, 0)])
        self.drag_coefficients = Graph([(-30,0.3),(-10, 0.1), (0, 0.07), (8, 0.1), (12, 0.14), (15, 0.25), (18, 0.45)])
        self.pressure_posns = Graph([(-10, 0), (0, 0.0)])
        self.angle_of_attack = None       
        self.angle_of_wing = None 
        self.brake = False
        self.let_up = False
        # list of (front line length, rear line legnth)
        self.line_wave_lengths = eval( open("line_lengths.points", "r").read() )
        
    def get_lift_coefficient(self, angle):
        return self.lift_coefficients.get_y_at_x(angle)
        
    def get_drag_coefficient(self, angle):
        return self.drag_coefficients.get_y_at_x(angle) * 1.1
        
    def get_pressure_pos(self, angle):
        return self.pressure_posns.get_y_at_x(angle)
        
    def get_front_length(self, frame):
        return self.line_wave_lengths[frame][0]   
        
    def get_rear_length(self, frame):
        return self.line_wave_lengths[frame][1]   
        
    def draw(self):
        draw_image(wingImg, wing_centre, self.body)
        
        #self.draw_shape()
        
        if draw_forces:
            # draw lift and drag
            self.draw_vector((self.pressure_pos, 0), self.lift, (0,0,255))
            self.draw_vector((self.pressure_pos, 0), self.drag, (255,0,0))
            self.draw_vector((0,0), Vec2d(1,0).rotated(self.angle_of_wing) * 500, (255,255,0))
            self.draw_vector((0,0), self.body.velocity * 300)
            self.draw_vector((0,0), self.body.velocity * (-300))
        
    def apply_force(self):
        self.angle_of_wing = self.body.angle - 3.1
        if self.brake:    
            self.angle_of_wing -= brake_angle
        elif self.let_up:
            self.angle_of_wing += brake_angle

        v, v_magn = self.body.velocity.normalized_and_length()
        angle_of_airflow = math.atan2(v.y, v.x)
        self.angle_of_attack = (angle_of_airflow - self.angle_of_wing) * 57
        if self.angle_of_attack > 180: self.angle_of_attack -= 360
        elif self.angle_of_attack < -180: self.angle_of_attack += 360
        
        # assuming lift is about 1000Nm ( 100kg ) at 10 m/s
        lift = 16.0 * v_magn * v_magn * self.get_lift_coefficient(self.angle_of_attack)
        drag = 16.0 * v_magn * v_magn * self.get_drag_coefficient(self.angle_of_attack)
        
        if lines_use_slide_joints:
            if lift < -4000:
                lift = -4000
            if lift > 4000:
                lift = 4000
            if drag > 4000:
                drag = 4000
            
        self.lift = -v.perpendicular() * lift
        self.drag = -v * drag
        
        self.pressure_pos = self.get_pressure_pos(self.angle_of_attack)
        
        world_pos = self.body.local_to_world((0,0))
        self.body.apply_force_at_world_point(self.lift + self.drag, world_pos)

        if thrust_on_wing:
            # 20 kg to the left
            world_pos = self.body.local_to_world((0,0))
            self.body.apply_force_at_world_point(Vec2d(-20 * 9.8, 0), world_pos)
            
        if line_wave:
            # up and down
            global line_wave_time
            global line_wave_cycle_length
            
            front_length, rear_length = self.line_wave_lengths[line_wave_time]

            if rear_line != None:
                if lines_use_slide_joints:
                    rear_line.max = rear_length
                else:
                    rear_line.distance = rear_length
            if front_line != None:
                if lines_use_slide_joints:
                    front_line.max = front_length
                else:
                    front_line.distance = front_length

            line_wave_time += 1
            if line_wave_time >= line_wave_cycle_length:
                line_wave_time = 0
        
class Centre(GameBody):
    def __init__(self, alt):
        poly_pts = [(-0.005, -0.005), (-0.005, 0.005), (0.005, 0.005), (0.005, -0.005)]
        GameBody.__init__(self, (0,alt), start_v, 3, poly_pts)
        
    def draw(self):
        self.draw_shape()
        
    def apply_force(self):
        if thrust:
            # 20 kg to the left
            world_pos = self.body.local_to_world((0,0))
            #self.body.apply_force_at_world_point(Vec2d(-20 * 9.8, 0), world_pos)
        self.apply_parasitic_drag(0.1)
        
class Damper(GameBody):
    def __init__(self, wing, pos_on_wing):
        self.wing = wing
        world_pos = wing.body.local_to_world(pos_on_wing)
        poly_pts = [(-0.05, -0.05), (-0.05, 0.05), (0.05, 0.05), (0.05, -0.05)]
        GameBody.__init__(self, world_pos + (0, -0.3), start_v, 0.5, poly_pts)
        self.damped_spring = pymunk.DampedSpring(wing.body, self.body, pos_on_wing, (0, 0), 0.3, 500, 0.3)
        space.add(self.damped_spring)
        
    def draw(self):
        draw_shape(self)

class Pilot(GameBody):
    def __init__(self, starting_height):
        poly_pts = [(0.302, 0.619),(-0.556, -0.0317),(-0.603, -0.714),(0.063, -0.460),(0.429, 0.222)]
        GameBody.__init__(self, (0,starting_height), start_v, 85, poly_pts)
        self.winch_up = False
        self.v_to_centre = None
        self.dline = 0.0
        if pilot_runs:      
            self.shape.friction = 0.0
        
    def draw(self):
        #self.draw_shape()
        draw_image(pilotImg, pilot_centre, self.body)
        if self.v_to_centre != None:
            self.draw_vector((-0.1, 0.2), self.v_to_centre * 100, (150,0,0))
        
    def apply_force(self):
        if thrust:
            # 20 kg to the left
            world_pos = self.body.local_to_world((0,0))
            self.body.apply_force_at_world_point(Vec2d(-20 * 9.8, 0), world_pos)

        # winch
#        if drop_line != None:
#            if self.winch_up:
#                self.dline -= 0.002
#                if self.dline < -0.4:
#                    self.dline = -0.4
#            else:
#                self.dline += 0.002
#                if self.dline > 0.4:
#                    self.dline = 0.4
#            drop_line.max += self.dline
#            if drop_line.max < 0.5:
#                drop_line.max = 0.5
#                self.dline = 0
#            if drop_line.max > winch_length:
#                drop_line.max = winch_length
#                self.dline = 0
        
        #self.apply_parasitic_drag(0.1)
            
    
def draw_line(s,e,col=(0,0,0)):
    pygame.draw.line(screen, col, world_to_screen(Vec2d(s[0], s[1])), world_to_screen(Vec2d(e[0], e[1])))
    
def draw_rect(minxy, maxxy, col=(0,0,0)):
    sminxy = world_to_screen(minxy)
    smaxxy = world_to_screen(maxxy)
    pygame.draw.rect(screen, col, pygame.Rect(sminxy.x, smaxxy.y, smaxxy.x - sminxy.x, sminxy.y - smaxxy.y))
    
def draw_text(s, col=(0,0,0)):
    global text_y
    screen.blit(myfont.render(s, False, col),(0,text_y))
    text_y += font_height * 1.2

def draw_background():
    # find min point
    minxy = Vec2d(0,h)
    maxxy = Vec2d(w,0)
    wmin = screen_to_world(minxy)
    wmax = screen_to_world(maxxy)
    space = background_spacing
    minx = int(wmin.x/space - 1) * space
    miny = int(wmin.y/space - 1) * space
    miny_above_ground = miny
    draw_ground = False
    if miny_above_ground < 0:
        miny_above_ground = 0
        draw_ground = True        
    maxx = int(wmax.x/space + 1) * space
    maxy = int(wmax.y/space + 1) * space
    
    x = minx
    while x < maxx:
        draw_line((x, miny_above_ground), (x, maxy), (128,128,128))
        x += space
    
    y = miny_above_ground
    while y < maxy:
        draw_line((minx, y), (maxx, y), (128,128,128))
        y += space
        
    if draw_ground:
        draw_rect(Vec2d(minx, miny), Vec2d(maxx, 0), (35,100,40))    
        
    if line_wave:
        if front_line != None:
            if lines_use_slide_joints:
                line_h = front_line.max * 30
            else:
                line_h = front_line.distance * 30
            pygame.draw.rect(screen, (0,255,0), pygame.Rect(0.8 * w, h - 100 - line_h, 10, line_h))
        if rear_line != None:
            if lines_use_slide_joints:
                line_h = rear_line.max * 30
            else:
                line_h = rear_line.distance * 30
            pygame.draw.rect(screen, (255,0,0), pygame.Rect(0.8 * w + 20, h - 100 - line_h, 10, line_h))

    draw_text(sim_mode) # gliding for example

    if wing.angle_of_attack != None:
        draw_text('Angle of attack = ' + ('%.1f' % wing.angle_of_attack) + ' degrees')
    
    draw_text('Height = ' + '%.1f' %(pilot.body.position.y) + 'm')
    draw_text('Airspeed = ' + '%.1f' % abs(wing.body.velocity) + 'm/s')
    draw_text('Distance = ' + '%.1f' % math.fabs(pilot.body.position.x) + 'm')
    draw_text('Normal Speed' if (fast_forward == 1) else ('>> x' + str(fast_forward)))
    #draw_text('Frame: ' + str(int(line_wave_time)) + ' of ' + str(line_wave_cycle_length))

def add_wall(space, start, end):
    seg = pymunk.Segment(space.static_body, start, end, 0.05)
    seg.friction = 1
    seg.elasticity = 1
    space.add(seg)
    
def y_flipped(pos):
    return Vec2d(pos.x, h-pos.y)
    
def camera_adjusted(pos):
    new_pos = (pos - camera) * pixel_scale + Vec2d(w * 0.5, h * 0.5)
    return new_pos

def world_to_screen(pos):
    return y_flipped(camera_adjusted(pos))
    
def screen_to_world(pos):
    new_pos = y_flipped(pos)
    return (new_pos - Vec2d(w * 0.5, h * 0.5))/pixel_scale + camera
    
def draw_image(img, centre, body):
    # centre is in pixels
    rect = img.get_rect()
    rect_center_to_img_center = Vec2d(centre.x - rect.centerx, rect.centery - centre.y)
    if body.angle > 1000:
        return
    if body.angle < -1000:
        return
    rot_img = pygame.transform.rotate(img, body.angle * 57)
    rect_center_to_img_center = rect_center_to_img_center.rotated(body.angle)
    rot_rect = rot_img.get_rect()
    v_centre = Vec2d(rot_rect.centerx, rot_rect.centery)
    rot_pos = rect_center_to_img_center + v_centre
    screen.blit(rot_img, world_to_screen(body.position) + Vec2d(-rot_pos.x, rot_pos.y - rot_rect.h))
    
def get_rope_vector(rope):
    return rope.a.local_to_world(rope.anchor_a) - rope.b.local_to_world(rope.anchor_b)

def draw_rope(rope):
    # draw a slide joint
    if rope == None:
        return
    
    draw_line(rope.a.local_to_world(rope.anchor_a), rope.b.local_to_world(rope.anchor_b), (128, 128, 160))
    
def update_camera_pos():
    global camera
    camera = pilot.body.position + (0,5)

# container
add_wall(space, (-20000, 0), (20000, 0))


drop_line = None
if winch:
    wing = Wing(start_height + 6 + winch_length * 2)
    centre = Centre(start_height + winch_length * 2)
    pilot = Pilot(start_height-0.2 + winch_length)
    line_attacher = centre
    if lines_use_slide_joints:
        drop_line = pymunk.SlideJoint(centre.body, pilot.body, (0, 0), (0.0, 0.2), 0.01, winch_length)
    else:
        drop_line = pymunk.PinJoint(centre.body, pilot.body, (0, 0), (0.0, 0.2))
        #drop_line.distance = winch_length
    space.add(drop_line)
    attacher_point = (0.0, 0.0)
else:
    wing = Wing(start_height + 6)
    pilot = Pilot(start_height-0.2)
    line_attacher = pilot
    attacher_point = (0.0, 0.2)
 
#damper_front = Damper(wing, (-1.3, 0))
#damper_rear = Damper(wing, (1.4, 0))

front_length, rear_length = wing.line_wave_lengths[start_frame]

if lines_use_slide_joints:
    front_line = pymunk.SlideJoint(wing.body, line_attacher.body, (-1.3, 0), attacher_point, 0.05, front_length)
#    front_line.max_force = 3000
    space.add(front_line)
    rear_line = pymunk.SlideJoint(wing.body, line_attacher.body, (1.4, 0), attacher_point, 0.05, rear_length)
#    rear_line.max_force = 3000
    space.add(rear_line)
else:
    front_line = pymunk.PinJoint(wing.body, line_attacher.body, (-1.3, 0), attacher_point)
    front_line.distance = front_length
    space.add(front_line)
    rear_line = pymunk.PinJoint(wing.body, line_attacher.body, (1.4, 0), attacher_point)
    rear_line.distance = rear_length
    space.add(rear_line)
    
#damped_spring_front = pymunk.DampedSpring(wing.body, line_attacher.body, (-1.3, 0), (0.0, 0.2), default_front_length, 5000, 0.3)
#space.add(damped_spring_front)
#damped_spring_rear = pymunk.DampedSpring(wing.body, line_attacher.body, (1.4, 0), (0.0, 0.2), default_rear_length, 5000, 0.3)
#space.add(damped_spring_rear)


game_step = 0.0

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                running = not running
            if event.key == pygame.K_ESCAPE:
                exit()
            if event.key == pygame.K_a:
                space.remove(front_line)
                front_line = None
            if event.key == pygame.K_b:
                space.remove(rear_line)
                rear_line = None
            if event.key == pygame.K_c:
                thrust = not thrust
            if event.key == pygame.K_d:
                wing.brake = True
            if event.key == pygame.K_e:
                pilot.winch_up = True
            if event.key == pygame.K_f:
                wing.let_up = True
            if event.key == pygame.K_g:
                thrust_on_wing = not thrust_on_wing
            if event.key == pygame.K_h:
                line_wave = not line_wave
                line_wave_time = start_frame
            if event.key == pygame.K_k:
                if fast_forward == 1:
                    fast_forward = 10
                elif fast_forward == 10:
                    fast_forward = 100
                else:
                    fast_forward = 1
            if event.key == pygame.K_l:
                if fast_forward == 1:
                    fast_forward = 0.25
                elif fast_forward == 0.25:
                    fast_forward = 0.1
                else:
                    fast_forward = 1
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_d:
                wing.brake = False
            if event.key == pygame.K_e:
                pilot.winch_up = False
            if event.key == pygame.K_f:
                wing.let_up = False

    screen.fill(pygame.Color(10,101,178))

    if running:
        step = fast_forward
        if fast_forward < 1.0:
            game_step += fast_forward
            if game_step < 1.0:
                step = 0
            else:
                step = 1
                game_step = 0.0
                
        for i in range(0, step):
            wing.apply_force()
            pilot.apply_force()
            space.step(1.0 / 60)
        
    update_camera_pos()
    
    text_y = 0

    draw_background()
    pilot.draw()
    wing.draw()
    draw_rope(front_line)
    draw_rope(rear_line)
    draw_rope(drop_line)
    
    pygame.display.flip()

    clock.tick(60)
    pygame.display.set_caption(f"fps: {clock.get_fps()}")
    
