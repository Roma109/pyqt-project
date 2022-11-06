import random
import sys

from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget


DEFAULT_MAX_HP = 20
DEFAULT_DAMAGE = 4
MAIN_MENU_STATE = 'MAIN_MENU'
IN_GAME_STATE = 'IN_GAME'
RESULTS_STATE = 'RESULTS'


class EnemyData:

    def __init__(self, picture, hp, damage, abilities, name):
        self.picture = picture
        self.hp = hp
        self.damage = damage
        self.abilities = abilities
        self.name = name


class EnemyGenerator:

    def __init__(self, game):
        self.game = game
        self.enemies = [EnemyData('clown.jpg', 5, 5, [HealingAbility()], "Джестер"),
                        EnemyData('mushroom.jpg', 20, 2, [HealingAbility()], 'Мухомор'),
                        EnemyData('stone-golem.png', 30, 1, [HealingAbility(), BlockAbility()], 'Каменный голем')]

    def generate_enemy(self, difficulty):
        enemy_data = self.enemies[random.randint(0, len(self.enemies) - 1)]
        return Enemy(int(enemy_data.hp * 1.25 ** difficulty),
                     int(enemy_data.damage * 1.25 ** difficulty),
                     enemy_data.abilities,
                     enemy_data.name,
                     self.game,
                     enemy_data.picture)


class Game(QMainWindow):

    def __init__(self):
        super().__init__()
        self.player = Player(DEFAULT_MAX_HP, DEFAULT_DAMAGE, self)
        self.enemy_generator = EnemyGenerator(self)
        self.state = None
        self.show_main_menu()

    def generate_enemy(self, difficulty): # сложность - количество побеждённых до этого врагов
        return self.enemy_generator.generate_enemy(difficulty)


    def save(self):
        pass

    def load(self):
        pass

    def show_main_menu(self):
        if self.state is not None:
            self.state.close()
        self.state = MainMenu(self)
        self.state.show()

    def show_game_window(self):
        self.state.close()
        self.state = GameWindow(self)
        self.state.show()

    def get_player(self):
        return self.player


# цикл сражения - хранит информацию о текущем враге и отвечает за ходы, обновляется после победы над врагом
class Cycle:

    def __init__(self, game_state, enemy):
        self.game_state = game_state
        self.enemy = enemy
        self.current_move = game_state.game.get_player()

    def step(self):
        if type(self.current_move) is Player:
            if not self.enemy.is_alive():
                self.game_state.progress()
                self.game_state.update()
                self.game_state.serve_cycle()
                return
            self.current_move = self.enemy
            self.current_move.step()
            self.step()
        else:
            if not self.game_state.game.player.is_alive():
                print("GAME OVER")
                self.game_state.close()
                return
            self.current_move = self.game_state.game.player
            self.current_move.step()
            self.game_state.update()


class MainMenu(QWidget):

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.initUi()

    def initUi(self):
        uic.loadUi('main_menu.ui', self)
        self.newGameButton.clicked.connect(self.start)

    def start(self):
        self.game.show_game_window()

    def state_code(self):
        return MAIN_MENU_STATE


class GameWindow(QWidget):

    def __init__(self, game, difficulty=0):
        super().__init__()
        self.game = game
        self.difficulty = difficulty
        self.initUi()
        self.serve_cycle()

    def initUi(self):
        uic.loadUi('game_menu.ui', self)
        self.attackButton.clicked.connect(self.attack)
        self.healButton.clicked.connect(self.heal)

    def state_code(self):
        return IN_GAME_STATE

    def write(self, message):
        self.textBrowser.append(message)

    def attack(self):
        # TODO: вынести атаку в способности
        self.game.player.attack(self.cycle.enemy)
        self.cycle.step()

    def heal(self):
        self.game.player.abilities[0].use(self.game.player)
        self.cycle.step()

    def serve_cycle(self):
        self.textBrowser.clear()
        self.cycle = Cycle(self, self.game.generate_enemy(self.difficulty))
        self.update_enemy()
        self.update_player()
        self.enemyName.setText(self.cycle.enemy.name)
        self.enemyPicture.setPixmap(QPixmap('assets\\enemies\\' + self.cycle.enemy.picture))
        self.difficulty += 1

    def progress(self):
        self.game.player.upgrade()

    def update(self):
        self.update_enemy()
        self.update_player()

    def update_enemy(self):
        self.enemyHp.setText(f'Здоровье: {int(self.cycle.enemy.hp)} из {int(self.cycle.enemy.maxhp)}')
        self.enemyDamage.setText(f'Урон: {int(self.cycle.enemy.get_damage())}')

    def update_player(self):
        self.playerHp.setText(f'Здоровье: {int(self.game.player.hp)} из {int(self.game.player.maxhp)}')
        self.playerDamage.setText(f'Урон: {int(self.game.player.get_damage())}')


class GameOverWindow(QWidget):

    def __init__(self):
        super().__init__()

    def initUi(self):
        pass


class Entity:

    def __init__(self, maxhp, damage, abilities, name, game):
        self.maxhp = maxhp
        self.hp = maxhp
        self.dmg = damage
        self.abilities = abilities
        self.name = name
        self.game = game
        self.effects = []

    def get_damage(self):
        dmg = self.dmg
        for effect in self.effects:
            dmg = effect.modify_damage(dmg)
        return dmg

    def damage(self, amount):
        for effect in self.effects:
            amount = effect.modify_incoming_damage(amount)
        self.hp = max(0, self.hp - amount)
        return amount

    def heal(self, amount):
        self.hp = min(self.maxhp, self.hp + amount)

    def kill(self):
        self.hp = 0

    def is_alive(self):
        return self.hp > 0

    def attack(self, target, message='%target% атакован существом %entity%'):
        self.game.state.write(message
                         .replace('%target%', target.name)
                         .replace('%entity%', self.name))
        damage = self.get_damage()
        self.game.state.write(f"Нанесено урона: {int(target.damage(damage))}")

    def add_effect(self, effect):
        self.effects.append(effect)

    def step(self): # вызывается когда ход переходит к этому энтити
        for effect in self.effects:
            effect.update()
            if effect.duration == 0:
                effect.discard()
                self.effects.remove(effect)


class Player(Entity):

    def __init__(self, maxhp, damage, game):
        super().__init__(maxhp, damage, [HealingAbility()], 'Игрок', game)
        self.killed = 0

    def upgrade(self):
        self.maxhp = self.maxhp * 1.2
        self.dmg = self.dmg * 1.2
        self.heal(self.maxhp * 0.2)

    def attack(self, target, message='%target% атакован игроком'):
        return super().attack(target, message)


class Enemy(Entity):

    def __init__(self, maxhp, damage, abilities, name, game, picture):
        super().__init__(maxhp, damage, abilities, name, game)
        self.picture = picture
        self.ai = EnemyAI(self)

    def step(self):
        return self.ai.step()


class Effect:

    def __init__(self, duration, name, entity):
        self.duration = duration
        self.name = name
        self.entity = entity

    def modify_damage(self, amount): # вызывается при атаке существом
        return amount

    def modify_incoming_damage(self, amount): # вызывается при атаки существа
        return amount

    def update(self): # вызывается когда ход переходит к энтити, наделённому данным эффектом
        self.duration -= 1

    def discard(self): # вызывается когда эффект снимается с энтити
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
        entity.game.state.write(f'{entity.name} исцелился')
        entity.heal(int(entity.maxhp * 0.2))


class BlockAbility(Ability):

    def __init__(self):
        super().__init__('блок')

    def use(self, entity):
        entity.game.state.write(f'{entity.name} использует блок')
        entity.add_effect(BlockEffect(1, 0.5, entity))


class EnemyAI:

    def __init__(self, entity):
        self.entity = entity

    def step(self):
        rand = random.randint(1, 4)
        if rand == 4:
            ability = self.entity.abilities[random.randint(0, len(self.entity.abilities) - 1)]
            ability.use(self.entity)
        else:
            self.entity.attack(self.entity.game.get_player())


def main():
    app = QApplication(sys.argv)
    game = Game()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
