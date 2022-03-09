#! /usr/bin/python3

import sys
import pygame  
from dataclasses import dataclass
import enum
import random
from paho.mqtt import client as mqtt_client
import json

@enum.unique
class Direction(enum.Enum):
    Up = 1
    Left = 2
    Down= 3
    Right = 4
    
    def flip(self):
        if self is Direction.Up:
            return Direction.Down
        elif self is Direction.Left:
            return Direction.Right
        elif self is Direction.Down:
            return Direction.Up
        elif self is Direction.Right:
            return Direction.Left
            
        raise Exception("Unexpected Direction")

@dataclass(frozen=True)
class Point:
    x: int
    y: int
        
    def as_tuple(self):
        return (self.x, self.y)
               
    def move_by(self, direction: (int, int)):
        return Point(self.x + direction[0], self.y + direction[1])

@dataclass
class Snake:
    """ The Snake """
    tail: [Point]
    maxlength: int
    direction: Direction   

    def __init__(self, tail = [Point(0,0)], direction = Direction.Right, maxlength = 10):
        self.direction = direction
        self.maxlength = maxlength
        self.tail = tail
        
    def update_direction(self, direction):
        if(direction is not self.direction.flip()): 
            self.direction = direction
            
    def head(self):
        return self.tail[-1]
        
    def move(self):     
        def next_move(head):
            if self.direction == Direction.Up:
                return head.move_by((0,-1))
            elif self.direction == Direction.Left:
                return head.move_by((-1,0))
            elif self.direction == Direction.Down:
                return head.move_by((0,1))
            else:
                return head.move_by((1,0))
        
        self.tail.append(next_move(self.head()))
            
        if len(self.tail) > self.maxlength:
            self.tail.pop(0)
            
    def is_selfcollision(self):
        return self.tail[-1] in self.tail[:-1]
    
        
class MQTTAdapter:
    """ MQTT Snake network controller """
    
    topic: str
    player_name : str
    remote_player_name : str
    client: mqtt_client.Client

    def __init__(self, player_name, remote_player_name, broker = 'broker.emqx.io', port = 1883, topic = "mqttsnake"):
        # generate client ID with pub prefix randomly
        client_id = f'python-mqtt-{random.randint(0, 1000)}'
        username = 'emqx'
        password = 'public'
        
        def connect_mqtt():
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    print("Connected to MQTT Broker!")
                else:
                    print("Failed to connect, return code %d\n", rc)

            client = mqtt_client.Client()
            client.username_pw_set(username, password)
            client.on_connect = on_connect
            client.connect(broker, port)
            return client
        
        self.topic = topic
        self.player_name = player_name
        self.remote_player_name = remote_player_name

        self.client = connect_mqtt()
    
    def _fruitpos_topic(self):
        return f"{self.topic}/fruitpos"
        
    def _remote_player_topic(self):
        return f"{self.topic}/{self.remote_player_name}"
        
    def _this_player_topic(self):
        return f"{self.topic}/{self.player_name}"
        
    def connect(self, update_snake_callback, update_fruit_callback):
        self.client.subscribe(f"{self.topic}/#")
       
        self.client.message_callback_add(self._remote_player_topic(), update_snake_callback)
        self.client.message_callback_add(self._fruitpos_topic(), update_fruit_callback)
        
        self.client.loop_start()
        
    def publish_player(self, snake):
 
        snake_tail = [ x.as_tuple() for x in snake.tail ]
        
        msg = json.dumps(snake_tail)
        result = self.client.publish(self._this_player_topic(), msg)
        
        if result[0] != 0:
            print(f"Failed to send message {msg} to topic {topic}")
            
            
    def publish_fruit(self, fruit_pos):
        msg = json.dumps(fruit_pos.as_tuple())

        result = self.client.publish(self._fruitpos_topic(), msg)
        
        if result[0] != 0:
            print(f"Failed to send message {msg} to topic {topic}")

class SnakeGame:
    """ The Snake Game"""
    
    snake: Snake
    fruit_pos: Point

    board_width: int
    board_height: int
    pixel_width: int
    
    screen: pygame.Surface
    fps: int
    save_border_width: int
    
    mqtt_adapter: MQTTAdapter
    remote_snake: Snake
  
    def __init__(self, board_width = 80, board_height = 60, pixel_width = 15, snake = None, fruit_pos= None, mqtt_adapter = None, save_border_percent = 20):
        self.board_width = board_width
        self.board_height = board_height
        self.pixel_width = pixel_width
        self.snake = snake
        self.remote_snake = None
        self.mqtt_adapter = mqtt_adapter       
        self.fruit_pos = fruit_pos
        self.screen = pygame.display.set_mode((board_width * pixel_width, board_height * pixel_width))
        self.fps = 5
        self.save_border_width = int(save_border_percent / 100 * min(board_width, board_height))

    def _random_point(self):
        return Point(random.randint(self.save_border_width, self.board_width - self.save_border_width), random.randint(self.save_border_width, self.board_height - self.save_border_width))
        
    def _to_rect(self, x, y):
            px = x * self.pixel_width
            py = y * self.pixel_width
            return pygame.Rect(px, py, self.pixel_width, self.pixel_width)
        
    def draw_fruit(self):
        p = self.fruit_pos
        pygame.draw.rect(self.screen, (255, 100, 100), self._to_rect(p.x, p.y))
        
    def draw_snake(self):  
        for t in self.snake.tail:
            pygame.draw.rect(self.screen, (0, 100, 0), self._to_rect(t.x, t.y))
    
    def draw_board(self):
        self.screen.fill((50, 50, 50))
        self.draw_fruit()
        self.draw_snake()
        
        if self.remote_snake:
            for t in self.remote_snake.tail:
                pygame.draw.rect(self.screen, (0, 0, 100), self._to_rect(t.x, t.y))
            
        pygame.display.flip()
        
    def is_collision(self):
        p = self.snake.head()
        return p.x < 0 or p.y < 0 or p.x > self.board_width or p.y > self.board_height or self.snake.is_selfcollision()
        
    def handle_fruit(self):
        if self.snake.head() == self.fruit_pos:
            self.snake.maxlength += 1
            self.fruit_pos = self._random_point()
            
            if self.mqtt_adapter:
                self.mqtt_adapter.publish_fruit(self.fruit_pos)
               
    def lose_game(self):
        self.write_on_screen("Game Over")
        pygame.time.wait(3000)


    def write_on_screen(self, msg):
        if pygame.font:
            font = pygame.font.Font(None, 128)
            text = font.render(msg, True, (200, 200, 200))
            textpos = text.get_rect(centerx=self.screen.get_width() / 2, centery=self.screen.get_height() / 2)
            self.screen.blit(text, textpos)
            pygame.display.flip()
    
    def player_control_or_quit(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.snake.update_direction(Direction.Left)
                elif event.key == pygame.K_RIGHT:
                    self.snake.update_direction(Direction.Right)
                elif event.key == pygame.K_UP:
                    self.snake.update_direction(Direction.Up)
                elif event.key == pygame.K_DOWN:
                    self.snake.update_direction(Direction.Down)
            
        return False

    def update_snake_callback(self, client, userdata, msg):
        self.remote_snake.tail = [ Point(x[0], x[1]) for x in json.loads(msg.payload.decode()) ]
    
    def update_fruit_callback(self, client, userdata, msg):
        x = json.loads(msg.payload.decode())
        self.fruit_pos = Point(x[0], x[1])

    def run_game(self):
        if not self.snake:
            self.snake = Snake(tail=[self._random_point()])

        if not self.fruit_pos:
            self.fruit_pos = self._random_point()

        fps_clock = pygame.time.Clock()

        if self.mqtt_adapter:
            self.mqtt_adapter.connect(update_snake_callback = self.update_snake_callback, update_fruit_callback = self.update_fruit_callback)
            self.remote_snake = Snake(tail=[])
            self.mqtt_adapter.publish_fruit(self.fruit_pos)
            self.mqtt_adapter.publish_player(self.snake)

            while len(self.remote_snake.tail) == 0:
                self.write_on_screen("Waiting for other player")
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return

                fps_clock.tick(self.fps)

        self.game_loop(fps_clock)

    def game_loop(self, fps_clock):
        non_collision_countdown = len(self.snake.tail) + 1
        while True:
            if self.player_control_or_quit():
                return

            self.snake.move()
            self.handle_fruit()

            if self.mqtt_adapter:
                self.mqtt_adapter.publish_player(self.snake)
                
                if non_collision_countdown > 0:
                    non_collision_countdown -= 1
                elif self.snake.head() in self.remote_snake.tail:
                    self.lose_game()
                    return

            if self.is_collision():
                self.lose_game()
                return
            else:
                self.draw_board()

            fps_clock.tick(self.fps)          
   
def main():
    pygame.init()
    
    snake_game = None
    if len(sys.argv) > 1:
       mqtt_adapter = MQTTAdapter(sys.argv[1], sys.argv[2])
       snake_game = SnakeGame(mqtt_adapter = mqtt_adapter)
    else:
       snake_game = SnakeGame()
    
    snake_game.run_game()
    pygame.quit()
    
if __name__ == "__main__":
    main()
