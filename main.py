import datetime
import random
import sqlite3
import sys

from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

DEFAULT_MAX_HP = 20
DEFAULT_DAMAGE = 4
ENEMIES = ['Джестер', "Мухомор", "Каменный голем"]


class EnemyData:

    def __init__(self, id, picture, hp, damage, abilities, name):
        self.id = id
        self.picture = picture
        self.hp = hp
        self.damage = damage
        self.abilities = abilities
        self.name = name


class EnemyGenerator:

    def __init__(self, game_state):
        self.game_state = game_state
        self.enemies = [EnemyData(0, QPixmap('assets\\enemies\\clown.jpg'), 5, 5, [HealingAbility()], ENEMIES[0]),
                        EnemyData(1, QPixmap('assets\\enemies\\mushroom.jpg'), 20, 2, [HealingAbility()], ENEMIES[1]),
                        EnemyData(2, QPixmap('assets\\enemies\\stone-golem.png'), 30, 1,
                                  [HealingAbility(), BlockAbility()], ENEMIES[2])]

    def generate_enemy(self, difficulty, id=-1, hp=-1):
        enemy_data = self.enemies[id if id != -1 else random.randint(0, len(self.enemies) - 1)]
        enemy = Enemy(enemy_data.id,
                      int(enemy_data.hp * 1.25 ** difficulty),
                      int(enemy_data.damage * 1.25 ** difficulty),
                      enemy_data.abilities,
                      enemy_data.name,
                      self.game_state,
                      enemy_data.picture)
        if hp != -1:
            enemy.hp = hp
        return enemy


class Game(QMainWindow):

    def __init__(self):
        super().__init__()
        self.state = None
        self.show_main_menu()

    def save(self, game_state):
        self.clear_save()
        with open('save.txt', 'w') as file:
            file.write(str(game_state.difficulty) + '\n')
            file.write(str(game_state.cycle.enemy.id) + '\n')
            file.write(str(game_state.cycle.enemy.hp) + '\n')
            file.write(str(game_state.player.hp) + '\n')

    def load(self):
        try:
            with open('save.txt') as file:
                lines = file.readlines()
                if len(lines) != 4:
                    self.clear_save()
                    return None
                difficulty = int(lines[0])
                enemy_id = int(lines[1])
                enemy_hp = int(lines[2])
                player_hp = int(lines[3])
                return {'difficulty': difficulty,
                        'enemy_id': enemy_id,
                        'enemy_hp': enemy_hp,
                        'player_hp': player_hp}
        except FileNotFoundError:
            return None
        except:
            self.clear_save()
            return None

    def clear_save(self):
        try:
            with open("save.txt", 'r+') as file:
                file.truncate(0)
        except FileNotFoundError:
            pass

    def show_main_menu(self):
        if self.state is not None:
            self.state.close()
        self.state = MainMenu(self)
        self.state.show()

    def new_game(self):
        self.state.close()
        self.state = GameWindow(self)
        self.state.show()

    def load_game(self):
        self.state.close()
        self.state = GameWindow(self, self.load())
        self.state.show()

    def game_over(self):
        self.clear_save()

    def save_statistic(self, difficulty, killer, date=datetime.date.today()):
        date = str(date).replace('-', " ")
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(f"INSERT INTO 'STATISTICS' ('RESULT', 'DATE', 'KILLER_ID') "
                       f"VALUES ({difficulty}, '{date}', {killer})")
        connection.commit()
        cursor.close()
        connection.close()

    def load_best_stat(self):
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        result = cursor.execute("SELECT * FROM 'STATISTICS' ORDER BY RESULT ASC").fetchall()
        if len(result) == 0:
            return ()
        return result[0]


class Cycle:  # цикл сражения - хранит информацию о текущем враге и отвечает за ходы, обновляется после победы над врагом

    def __init__(self, game_state, enemy, player):
        self.game_state = game_state
        self.enemy = enemy
        self.player = player
        self.current_move = player

    def step(self):
        if type(self.current_move) is Player:
            if not self.enemy.is_alive():
                self.game_state.progress()
                self.game_state.update()
                self.game_state.serve_cycle()
                return
            self.current_move = self.enemy
            self.current_move.step()
            self.current_move.move()
            self.step()
        else:
            if not self.player.is_alive():
                self.game_state.game.save_statistic(self.game_state.difficulty, self.current_move.id)
                self.game_state.game.clear_save()
                self.game_state.game.show_main_menu()
                return
            self.current_move = self.player
            self.current_move.step()
            self.game_state.update()


class MainMenu(QWidget):

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.initUi()

    def initUi(self):
        uic.loadUi('main_menu.ui', self)
        self.newGameButton.clicked.connect(self.game.new_game)
        self.loadGameButton.clicked.connect(self.game.load_game)
        best_stat = self.game.load_best_stat()
        self.bestResultLabel.setText("Нету лучшего результата" if len(best_stat) == 0
                                     else f"{best_stat[2]}, Счёт {best_stat[1]}, Последний враг: {ENEMIES[best_stat[3]]}")


class GameWindow(QWidget):

    def __init__(self, game, data=None):
        super().__init__()
        if data is None:
            data = {}
        self.game = game
        self.difficulty = data.get('difficulty', 0)
        self.enemy_generator = EnemyGenerator(self)
        self.player = Player(self, self.difficulty)
        if 'player_hp' in data:
            self.player.hp = data['player_hp']
        self.initUi()
        self.serve_cycle(self.enemy_generator.generate_enemy(self.difficulty,
                                                             data.get('enemy_id', -1),
                                                             data.get('enemy_hp', -1)))

    def generate_enemy(self, difficulty=-1):  # сложность - количество побеждённых до этого врагов
        if difficulty == -1:
            difficulty = self.difficulty
        return self.enemy_generator.generate_enemy(difficulty)

    def initUi(self):
        uic.loadUi('game_menu.ui', self)
        self.attackButton.clicked.connect(self.attack)
        self.healButton.clicked.connect(self.heal)

    def write(self, message):
        self.textBrowser.append(message)

    def attack(self):
        # TODO: вынести атаку в способности
        self.player.attack(self.cycle.enemy)
        self.cycle.step()

    def heal(self):
        self.player.abilities[0].use(self.player)
        self.cycle.step()

    def serve_cycle(self, enemy=None):
        self.textBrowser.clear()
        if enemy is None:
            enemy = self.generate_enemy()
        self.cycle = Cycle(self, enemy, self.player)
        self.update_enemy()
        self.update_player()
        self.enemyName.setText(self.cycle.enemy.name)
        self.enemyPicture.setPixmap(self.cycle.enemy.picture)
        self.difficulty += 1

    def progress(self):
        self.player.upgrade()

    def update(self):
        self.update_enemy()
        self.update_player()

    def update_enemy(self):
        self.enemyHp.setText(f'Здоровье: {int(self.cycle.enemy.hp)} из {int(self.cycle.enemy.maxhp)}')
        self.enemyDamage.setText(f'Урон: {int(self.cycle.enemy.get_damage())}')

    def update_player(self):
        self.playerHp.setText(f'Здоровье: {int(self.player.hp)} из {int(self.player.maxhp)}')
        self.playerDamage.setText(f'Урон: {int(self.player.get_damage())}')

    def closeEvent(self, event):
        self.game.save(self)


class Entity:

    def __init__(self, maxhp, damage, abilities, name, game_state):
        self.maxhp = maxhp
        self.hp = maxhp
        self.dmg = damage
        self.abilities = abilities
        self.name = name
        self.game_state = game_state
        self.effects = []

    def get_damage(self):
        dmg = self.dmg
        for effect in self.effects:
            dmg = effect.modify_damage(dmg)
        return dmg

    def damage(self, amount):
        for effect in self.effects:
            amount = effect.modify_incoming_damage(amount)
        self.hp = int(max(0, self.hp - amount))
        return amount

    def heal(self, amount):
        self.hp = min(self.maxhp, self.hp + amount)

    def kill(self):
        self.hp = 0

    def is_alive(self):
        return self.hp > 0

    def attack(self, target, message='%target% атакован существом %entity%'):
        self.game_state.write(message
                              .replace('%target%', target.name)
                              .replace('%entity%', self.name))
        damage = self.get_damage()
        self.game_state.write(f"Нанесено урона: {int(target.damage(damage))}")

    def add_effect(self, effect):
        self.effects.append(effect)

    def step(self):  # вызывается когда ход переходит к этому энтити
        for effect in self.effects:
            effect.update()
            if effect.duration == 0:
                effect.discard()
                self.effects.remove(effect)


class Player(Entity):

    def __init__(self, game_state, difficulty=1, maxhp=DEFAULT_MAX_HP, damage=DEFAULT_DAMAGE):
        super().__init__(maxhp, damage, [HealingAbility()], 'Игрок', game_state)
        self.killed = 0
        if difficulty > 1:
            self.upgrade(difficulty)

    def upgrade(self, n=1):
        self.maxhp = self.maxhp * 1.2 ** n
        self.dmg = self.dmg * 1.2 ** n
        self.heal(self.maxhp * 0.2)

    def attack(self, target, message='%target% атакован игроком'):
        return super().attack(target, message)


class Enemy(Entity):

    def __init__(self, id, maxhp, damage, abilities, name, game_state, picture):
        super().__init__(maxhp, damage, abilities, name, game_state)
        self.id = id
        self.picture = picture
        self.ai = EnemyAI(self)

    def move(self):
        self.ai.step()


class Effect:

    def __init__(self, duration, name, entity):
        self.duration = duration
        self.name = name
        self.entity = entity

    def modify_damage(self, amount):  # вызывается при атаке существом
        return amount

    def modify_incoming_damage(self, amount):  # вызывается при атаки существа
        return amount

    def update(self):  # вызывается когда ход переходит к энтити, наделённому данным эффектом
        self.duration -= 1

    def discard(self):  # вызывается когда эффект снимается с энтити
        pass


class BlockEffect(Effect):

    def __init__(self, duration, block, entity):
        super().__init__(duration, 'блок', entity)
        self.block = block

    def modify_incoming_damage(self, amount):
        return amount * (1 - self.block)


class Ability:

    def __init__(self, name):
        self.name = name

    def use(self, entity):
        raise Exception('Override method "use" to create ability')


class HealingAbility(Ability):

    def __init__(self):
        super().__init__('исцеление')

    def use(self, entity):
        entity.game_state.write(f'{entity.name} исцелился')
        entity.heal(int(entity.maxhp * 0.2))


class BlockAbility(Ability):

    def __init__(self):
        super().__init__('блок')

    def use(self, entity):
        entity.game_state.write(f'{entity.name} использует блок')
        entity.add_effect(BlockEffect(1, 0.5, entity))


class EnemyAI:

    def __init__(self, entity):
        self.entity = entity

    def step(self):
        rand = random.randint(1, 3)
        if rand == 3:
            ability = self.entity.abilities[random.randint(0, len(self.entity.abilities) - 1)]
            ability.use(self.entity)
        else:
            self.entity.attack(self.entity.game_state.player)


def main():
    app = QApplication(sys.argv)
    game = Game()
    code = app.exec_()
    sys.exit(code)


if __name__ == '__main__':
    main()
