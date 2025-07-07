import logging
import os
import asyncio
import random
import re
from collections import defaultdict
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global userbot instance
_userbot_instance = None

class WordleUserBot:
    def __init__(self, api_id, api_hash, session_string):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.client = None
        self.active_games = {}  # chat_id: game_state
        self.word_list = []
        self.owner_bot_id = 7728440793
        self.sticker_sets = [
            "Webp_18",
            "Thoughtless_Planarian_by_fStikBot", 
            "Quby741",
            "sti_1611e_by_TgEmodziBot",
            "catsunicmass"
        ]
        self.sticker_enabled = True  # Default: stickers enabled
        self.load_words()

    def load_words(self):
        """Load 5-letter words from file"""
        try:
            with open('words.txt', 'r') as f:
                for line in f:
                    word = line.strip().lower()
                    if len(word) == 5 and word.isalpha():
                        self.word_list.append(word)
            logger.info(f"Loaded {len(self.word_list)} words for userbot")
        except FileNotFoundError:
            logger.error("words.txt file not found for userbot!")

    def get_random_word(self):
        """Get a random 5-letter word"""
        return random.choice(self.word_list).upper()

    def set_sticker_enabled(self, enabled):
        """Enable or disable sticker sending"""
        self.sticker_enabled = enabled
        logger.info(f"Sticker sending {'enabled' if enabled else 'disabled'}")

    async def send_random_sticker(self, chat_id):
        """Send a random sticker from predefined sticker sets"""
        if not self.sticker_enabled:
            logger.info(f"Sticker sending disabled, skipping sticker for chat {chat_id}")
            return

        try:
            from telethon.tl.functions.messages import GetStickerSetRequest
            from telethon.tl.types import InputStickerSetShortName

            # Choose random sticker set
            sticker_set_name = random.choice(self.sticker_sets)

            # Get stickers from the chosen set using correct API
            sticker_set = await self.client(GetStickerSetRequest(
                stickerset=InputStickerSetShortName(short_name=sticker_set_name),
                hash=0
            ))

            if sticker_set and sticker_set.documents:
                # Choose random sticker from the set
                random_sticker = random.choice(sticker_set.documents)

                # Send the sticker
                await self.client.send_file(chat_id, random_sticker)
                logger.info(f"Sent random sticker from {sticker_set_name} to chat {chat_id}")
            else:
                logger.warning(f"No stickers found in set {sticker_set_name}")

        except Exception as e:
            logger.error(f"Error sending sticker to chat {chat_id}: {e}")
            # If sticker sending fails, continue with the game

    def get_letter_frequency(self, words):
        """Get frequency of letters in remaining words"""
        freq = defaultdict(int)
        for word in words:
            for char in set(word):  # Use set to count each letter once per word
                freq[char] += 1
        return freq

    def score_word(self, word, letter_freq):
        """Score a word based on letter frequency"""
        score = 0
        used_letters = set()
        for char in word:
            if char not in used_letters:
                score += letter_freq[char]
                used_letters.add(char)
        return score

    def parse_wordle_result(self, message_text):
        """Parse Wordle result from bot response"""
        # Check for emoji patterns
        emoji_pattern = r'([🟥🟨🟩]\s*){5}'
        if re.search(emoji_pattern, message_text):
            return True
        return False

    def is_invalid_word_message(self, message_text):
        """Check if message indicates invalid word"""
        invalid_patterns = [
            "is not a valid word",
            "not a valid word",
            "invalid word"
        ]
        return any(pattern in message_text.lower() for pattern in invalid_patterns)

    def is_already_guessed_message(self, message_text):
        """Check if someone already guessed the word"""
        already_guessed_patterns = [
            "Someone has already guessed your word",
            "already guessed",
            "Please try another one"
        ]
        return any(pattern in message_text for pattern in already_guessed_patterns)

    def is_correct_guess_message(self, message_text):
        """Check if the guess was correct"""
        correct_patterns = [
            "Congrats! You guessed it correctly",
            "guessed correctly",
            "Start with /new",
            "Added",
            "leaderboard"
        ]
        # Check if message contains correct guess indicators
        contains_correct_pattern = any(pattern in message_text for pattern in correct_patterns)

        # More specific check for the exact pattern you mentioned
        if "Congrats! You guessed it correctly" in message_text and "Added" in message_text and "leaderboard" in message_text and "Start with /new" in message_text:
            return True

        return contains_correct_pattern

    def is_new_game_started_message(self, message_text):
        """Check if a new game was started"""
        new_game_patterns = [
            "I've started a new Wordle",
            "New Wordle started", 
            "Guess a 5-letter word",
            "new word is ready",
            "Wordle #",
            "started a new",
            "Word is ready",
            "Let's play Wordle",
            "Game started"
        ]
        return any(pattern in message_text for pattern in new_game_patterns)

    def extract_clues_from_message(self, message_text):
        """Extract clues from message with multiple guesses"""
        clues = []
        lines = message_text.strip().split('\n')

        # Mathematical Sans-Serif Bold Capital Letters mapping
        math_bold_to_regular = {
            '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H',
            '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P',
            '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X',
            '𝗬': 'Y', '𝗭': 'Z'
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Pattern for Mathematical Sans-Serif Bold format
            pattern_math_bold = r'([🟥🟨🟩]\s*){5}\s*([𝗔-𝗭]{5})'
            match_math_bold = re.search(pattern_math_bold, line)

            if match_math_bold:
                emoji_part = line.split(match_math_bold.group(2))[0].strip()
                emoji_result = re.sub(r'\s+', '', emoji_part)
                math_bold_word = match_math_bold.group(2)
                guess_word = ''.join(math_bold_to_regular.get(char, char) for char in math_bold_word).lower()
                clues.append((guess_word, emoji_result))

        return clues

    def get_last_word_from_message(self, message_text):
        """Get the last word from a multi-line bot response"""
        lines = message_text.strip().split('\n')

        # Mathematical Sans-Serif Bold Capital Letters mapping
        math_bold_to_regular = {
            '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H',
            '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P',
            '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X',
            '𝗬': 'Y', '𝗭': 'Z'
        }

        # Look at lines from bottom to top to find the last word
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            # Pattern for Mathematical Sans-Serif Bold format
            pattern_math_bold = r'([🟥🟨🟩]\s*){5}\s*([𝗔-𝗭]{5})'
            match_math_bold = re.search(pattern_math_bold, line)

            if match_math_bold:
                math_bold_word = match_math_bold.group(2)
                guess_word = ''.join(math_bold_to_regular.get(char, char) for char in math_bold_word).lower()
                return guess_word

        return None

    def filter_words_by_clues(self, clues):
        """Filter words based on all collected clues with advanced logic"""
        if not clues:
            return self.word_list

        valid_words = []

        for word in self.word_list:
            is_valid = True

            # Track letters we know are in the word and their constraints
            required_letters = set()
            forbidden_letters = set()
            position_constraints = {}  # position -> required letter
            position_forbidden = {}    # position -> set of forbidden letters

            # Analyze all clues first
            for guess_word, emoji_result in clues:
                for i, (guess_char, emoji) in enumerate(zip(guess_word, emoji_result)):
                    if emoji == '🟩':  # Green - correct letter, correct position
                        position_constraints[i] = guess_char
                        required_letters.add(guess_char)
                    elif emoji == '🟨':  # Yellow - correct letter, wrong position
                        required_letters.add(guess_char)
                        if i not in position_forbidden:
                            position_forbidden[i] = set()
                        position_forbidden[i].add(guess_char)
                    elif emoji == '🟥':  # Red - letter not in word
                        # Only mark as forbidden if it's not required elsewhere
                        if guess_char not in required_letters:
                            forbidden_letters.add(guess_char)

            # Check if word satisfies all constraints
            # 1. Check required positions (green letters)
            for pos, required_char in position_constraints.items():
                if word[pos] != required_char:
                    is_valid = False
                    break

            if not is_valid:
                continue

            # 2. Check forbidden letters (red letters that aren't required)
            word_letters = set(word)
            if forbidden_letters & word_letters:
                is_valid = False
                continue

            # 3. Check required letters are present (yellow letters)
            if not required_letters.issubset(word_letters):
                is_valid = False
                continue

            # 4. Check position forbidden constraints (yellow letters can't be in wrong spots)
            for pos, forbidden_chars in position_forbidden.items():
                if word[pos] in forbidden_chars:
                    is_valid = False
                    break

            if is_valid:
                valid_words.append(word)

        return valid_words

    def get_best_guess(self, clues, used_words=None):
        """Get the best next guess based on clues using advanced strategy"""
        if used_words is None:
            used_words = set()

        valid_words = self.filter_words_by_clues(clues)

        # Remove already used words (convert both to lowercase for comparison)
        valid_words = [word for word in valid_words if word.lower() not in {w.lower() for w in used_words}]

        if not valid_words:
            # If no valid words left, try random words that haven't been used
            remaining_words = [word for word in self.word_list if word.lower() not in {w.lower() for w in used_words}]
            if remaining_words:
                return random.choice(remaining_words).upper()
            else:
                return self.get_random_word()

        if len(valid_words) == 1:
            return valid_words[0].upper()

        # For first guess (no clues), use random word to avoid detection
        if not clues or len(clues) == 0:
            remaining_words = [word for word in self.word_list if word.lower() not in {w.lower() for w in used_words}]
            if remaining_words:
                return random.choice(remaining_words).upper()

        # If we have many options, prefer words with common letters and good coverage
        if len(valid_words) > 50:
            # Use high-frequency starting words for better elimination, but exclude used ones
            common_starters = ['arose', 'adieu', 'audio', 'ourie', 'louie', 'storm', 'court', 'plant', 'slice', 'crane']
            available_starters = [w for w in common_starters if w in self.word_list and w.lower() not in {word.lower() for word in used_words}]
            if available_starters and len(clues) < 2:
                return available_starters[0].upper()

        # Calculate letter frequencies in remaining words
        letter_freq = self.get_letter_frequency(valid_words)

        # Advanced scoring: consider letter uniqueness and position variety
        def advanced_score(word):
            base_score = self.score_word(word, letter_freq)

            # Bonus for words with unique letters (avoid repeated letters early)
            unique_letters = len(set(word))
            uniqueness_bonus = unique_letters * 10

            # Bonus for common letter positions
            position_bonus = 0
            for i, char in enumerate(word):
                # Count how many remaining words have this letter in this position
                position_count = sum(1 for w in valid_words if w[i] == char)
                if position_count > len(valid_words) * 0.1:  # If >10% of words have this letter here
                    position_bonus += position_count

            return base_score + uniqueness_bonus + position_bonus

        # Score all words and return the best one
        best_word = max(valid_words, key=advanced_score)
        return best_word.upper()

    async def start(self):
        """Start the userbot client"""
        from telethon.sessions import StringSession
        self.client = TelegramClient(StringSession(self.session_string), self.api_id, self.api_hash)
        await self.client.start()
        logger.info("Userbot started successfully")

        # Add event handler for incoming messages
        @self.client.on(events.NewMessage)
        async def handle_message(event):
            if event.sender_id == self.owner_bot_id:
                await self.handle_bot_response(event)

    async def handle_bot_response(self, event):
        """Handle responses from the Wordle bot"""
        chat_id = event.chat_id
        message_text = event.message.message

        if chat_id not in self.active_games:
            return

        game_state = self.active_games[chat_id]

        # IMMEDIATELY check if this is a correct guess message and stop all processing
        if self.is_correct_guess_message(message_text):
            logger.info(f"IMMEDIATE STOP: Correct guess detected in chat {chat_id}, stopping all processing")

            # IMMEDIATELY mark game as won and clear all data to prevent any further processing
            game_state['game_won'] = True
            game_state['clues'] = []
            game_state['used_words'] = set()
            game_state['last_guessed_word'] = None
            game_state['processing_stopped'] = True  # Add flag to stop all processing

            ultra_mode = game_state.get('ultra_mode', False)
            fast_mode = game_state.get('fast_mode', False)

            # Send sticker if enabled
            if self.sticker_enabled:
                if ultra_mode:
                    # Ultra fast sticker animation
                    choosing_delay = random.uniform(0.2, 0.8)
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(choosing_delay)
                else:
                    # Show choosing sticker animation (1.5 - 2.5 seconds)
                    choosing_delay = random.uniform(1.5, 2.5)
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(choosing_delay)

                # Send random sticker
                await self.send_random_sticker(chat_id)

            if ultra_mode:
                # Ultra fast mode
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                # Add delay before starting new game
                await asyncio.sleep(random.uniform(1.5, 3))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                # Add realistic delay before starting new game
                await asyncio.sleep(random.uniform(3, 6))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))

            # Start new game
            await self.client.send_message(chat_id, "/new")
            logger.info(f"Sent /new command for chat {chat_id}")

            # Schedule automatic first guess in case we don't get confirmation
            asyncio.create_task(self.ensure_new_game_starts(chat_id, ultra_mode, fast_mode))
            return

        # If game was just won or processing is stopped, ignore all responses except new game confirmation
        if game_state.get('game_won', False) or game_state.get('processing_stopped', False):
            if self.is_new_game_started_message(message_text):
                logger.info(f"New game confirmed after win in chat {chat_id}")
                # Reset game state completely
                game_state['clues'] = []
                game_state['used_words'] = set()
                game_state['game_won'] = False
                game_state['last_guessed_word'] = None
                game_state['processing_stopped'] = False  # Re-enable processing

                ultra_mode = game_state.get('ultra_mode', False)
                fast_mode = game_state.get('fast_mode', False)

                if ultra_mode:
                    # Ultra fast mode
                    await asyncio.sleep(random.uniform(0.2, 1.5))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(0.2, 0.8))
                elif fast_mode:
                    # Add delay before first guess
                    await asyncio.sleep(random.uniform(1.5, 3))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(1, 2))
                else:
                    # Add realistic delay before first guess
                    await asyncio.sleep(random.uniform(2, 5))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(1, 2))

                # Send first guess for new game
                first_guess = self.get_best_guess([], set())
                if first_guess:
                    game_state['used_words'].add(first_guess.lower())
                    game_state['last_guessed_word'] = first_guess.lower()
                    await self.client.send_message(chat_id, first_guess.capitalize())
                    logger.info(f"Started new game in chat {chat_id} with word: {first_guess}")
            else:
                logger.info(f"Ignoring message in chat {chat_id} because game was just won or processing stopped: {message_text[:50]}...")
            return

        # Check if processing has been stopped
        if game_state.get('processing_stopped', False):
            logger.info(f"Processing stopped for chat {chat_id}, ignoring message")
            return

        # Check if word is invalid
        if self.is_invalid_word_message(message_text):
            # Double-check if processing was stopped during the delay
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during invalid word handling")
                return

            logger.info(f"Invalid word in chat {chat_id}, trying another word")
            ultra_mode = game_state.get('ultra_mode', False)
            fast_mode = game_state.get('fast_mode', False)

            if ultra_mode:
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                await asyncio.sleep(random.uniform(1.5, 3))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                await asyncio.sleep(random.uniform(2, 4))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))

            # Check again if processing was stopped during the delay
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during invalid word delay")
                return

            # Try to get a better word based on current clues
            used_words = game_state.get('used_words', set())
            next_guess = self.get_best_guess(game_state['clues'], used_words)
            if next_guess and next_guess.lower() not in used_words:
                game_state.setdefault('used_words', set()).add(next_guess.lower())
                game_state['last_guessed_word'] = next_guess.lower()
                await self.client.send_message(chat_id, next_guess.capitalize())
                logger.info(f"Sent new word after invalid: {next_guess}")
            return

        # Check if someone already guessed
        if self.is_already_guessed_message(message_text):
            # Double-check if processing was stopped during the delay
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during already guessed handling")
                return

            logger.info(f"Word already guessed in chat {chat_id}, trying another word")
            ultra_mode = game_state.get('ultra_mode', False)
            fast_mode = game_state.get('fast_mode', False)

            if ultra_mode:
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                await asyncio.sleep(random.uniform(1.5, 3))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                await asyncio.sleep(random.uniform(2, 4))
                # Send typing action
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))

            # Check again if processing was stopped during the delay
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during already guessed delay")
                return

            # Try to get a better word based on current clues
            used_words = game_state.get('used_words', set())
            next_guess = self.get_best_guess(game_state['clues'], used_words)
            if next_guess and next_guess.lower() not in used_words:
                game_state.setdefault('used_words', set()).add(next_guess.lower())
                game_state['last_guessed_word'] = next_guess.lower()
                await self.client.send_message(chat_id, next_guess.capitalize())
                logger.info(f"Sent new word after already guessed: {next_guess}")
            else:
                logger.warning(f"Could not find new word for chat {chat_id}, all words may be used")
            return



        # Check if new game started (after /new command)
        if self.is_new_game_started_message(message_text):
            logger.info(f"New game started in chat {chat_id}")
            # Reset game state
            game_state['clues'] = []
            game_state['used_words'] = set()
            game_state['game_won'] = False
            ultra_mode = game_state.get('ultra_mode', False)
            fast_mode = game_state.get('fast_mode', False)

            if ultra_mode:
                # Ultra fast mode
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                # Add delay before first guess
                await asyncio.sleep(random.uniform(1.5, 3))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                # Add realistic delay before first guess
                await asyncio.sleep(random.uniform(2, 5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))

            # Send first guess for new game
            first_guess = self.get_best_guess([], set())
            if first_guess:
                game_state['used_words'].add(first_guess.lower())
                game_state['last_guessed_word'] = first_guess.lower()
                await self.client.send_message(chat_id, first_guess.capitalize())
                logger.info(f"Started new game in chat {chat_id} with word: {first_guess}")
            return

        # Check for Wordle result pattern
        if self.parse_wordle_result(message_text):
            # Double-check if processing was stopped
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during Wordle result handling")
                return

            # Check if the last word in the response matches our last guessed word
            last_word_in_response = self.get_last_word_from_message(message_text)
            last_guessed_word = game_state.get('last_guessed_word')

            if last_word_in_response and last_guessed_word:
                if last_word_in_response.lower() != last_guessed_word.lower():
                    logger.info(f"Ignoring response in chat {chat_id}: last word '{last_word_in_response}' doesn't match our guess '{last_guessed_word}'")
                    return
            elif last_word_in_response and not last_guessed_word:
                # If we don't have a last guessed word tracked, this might be from another user
                logger.info(f"Ignoring response in chat {chat_id}: no last guessed word tracked, response word: '{last_word_in_response}'")
                return

            logger.info(f"Got valid Wordle result in chat {chat_id} for our word: {last_guessed_word}")
            clues = self.extract_clues_from_message(message_text)
            if clues:
                game_state['clues'].extend(clues)
                logger.info(f"Updated clues for chat {chat_id}: {game_state['clues']}")

            ultra_mode = game_state.get('ultra_mode', False)
            fast_mode = game_state.get('fast_mode', False)

            if ultra_mode:
                # Ultra fast mode
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                # Add delay before next guess
                await asyncio.sleep(random.uniform(1.5, 3))
                # Send typing action to show we're thinking
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                # Add realistic delay before next guess (thinking time)
                await asyncio.sleep(random.uniform(3, 8))
                # Send typing action to show we're thinking
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(2, 4))

            # Check again if processing was stopped during the delay
            if game_state.get('processing_stopped', False):
                logger.info(f"Processing stopped for chat {chat_id} during Wordle result delay")
                return

            # Get next best guess using advanced analysis
            used_words = game_state.get('used_words', set())
            next_guess = self.get_best_guess(game_state['clues'], used_words)
            if next_guess and next_guess.lower() not in used_words:
                game_state.setdefault('used_words', set()).add(next_guess.lower())
                game_state['last_guessed_word'] = next_guess.lower()
                logger.info(f"Next guess for chat {chat_id}: {next_guess}")
                await self.client.send_message(chat_id, next_guess.capitalize())
            else:
                logger.warning(f"Could not generate new guess for chat {chat_id}")

    async def get_groups(self):
        """Get list of groups the userbot is in"""
        try:
            groups = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    groups.append({
                        'id': dialog.id,
                        'title': dialog.title
                    })
            return groups
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []

    async def start_game_in_group(self, chat_id, fast_mode=False, ultra_mode=False):
        """Start a Wordle game in the specified group"""
        try:
            # Initialize game state with empty used words set and speed mode
            self.active_games[chat_id] = {
                'clues': [],
                'used_words': set(),
                'active': True,
                'fast_mode': fast_mode,
                'ultra_mode': ultra_mode,
                'game_won': False,
                'processing_stopped': False,
                'last_guessed_word': None
            }

            ultra_mode = self.active_games[chat_id].get('ultra_mode', False)
            fast_mode = self.active_games[chat_id].get('fast_mode', False)

            if ultra_mode:
                # Ultra fast timing
                await asyncio.sleep(random.uniform(0.2, 1.5))
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(0.2, 0.8))
            elif fast_mode:
                # Add delay before starting
                await asyncio.sleep(random.uniform(1.5, 3))
                # Send typing action to appear like a real user
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))
            else:
                # Add realistic delay before starting
                await asyncio.sleep(random.uniform(2, 4))
                # Send typing action to appear like a real user
                async with self.client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(1, 2))

            # Send first guess - use a strategic starting word
            first_guess = self.get_best_guess([], set())
            if first_guess:
                self.active_games[chat_id]['used_words'].add(first_guess.lower())
                self.active_games[chat_id]['last_guessed_word'] = first_guess.lower()
                await self.client.send_message(chat_id, first_guess.capitalize())
                logger.info(f"Started game in chat {chat_id} with word: {first_guess}")

        except Exception as e:
            logger.error(f"Error starting game in chat {chat_id}: {e}")
            raise

    async def stop_all_games(self):
        """Stop all active games"""
        self.active_games.clear()
        logger.info("Stopped all active games")

    async def ensure_new_game_starts(self, chat_id, ultra_mode=False, fast_mode=False):
        """Ensure new game starts even if we don't get confirmation message"""
        try:
            # Wait a bit longer for the confirmation message
            if ultra_mode:
                await asyncio.sleep(3)  # Wait 3 seconds for ultra mode
            elif fast_mode:
                await asyncio.sleep(5)  # Wait 5 seconds for fast mode  
            else:
                await asyncio.sleep(8)  # Wait 8 seconds for normal mode

            # Check if game is still marked as won (meaning no new game started)
            if chat_id in self.active_games and self.active_games[chat_id].get('game_won', False):
                logger.info(f"No new game confirmation received for chat {chat_id}, forcing new game start")

                # Reset game state
                game_state = self.active_games[chat_id]
                game_state['clues'] = []
                game_state['used_words'] = set()
                game_state['game_won'] = False
                game_state['last_guessed_word'] = None
                game_state['processing_stopped'] = False

                # Add small delay before first guess
                if ultra_mode:
                    await asyncio.sleep(random.uniform(0.2, 1.5))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(0.2, 0.8))
                elif fast_mode:
                    await asyncio.sleep(random.uniform(1.5, 3))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(1, 2))
                else:
                    await asyncio.sleep(random.uniform(2, 5))
                    async with self.client.action(chat_id, 'typing'):
                        await asyncio.sleep(random.uniform(1, 2))

                # Send first guess for new game
                first_guess = self.get_best_guess([], set())
                if first_guess:
                    game_state['used_words'].add(first_guess.lower())
                    game_state['last_guessed_word'] = first_guess.lower()
                    await self.client.send_message(chat_id, first_guess.capitalize())
                    logger.info(f"Force started new game in chat {chat_id} with word: {first_guess}")

        except Exception as e:
            logger.error(f"Error in ensure_new_game_starts for chat {chat_id}: {e}")

    async def stop(self):
        """Stop the userbot"""
        if self.client:
            await self.stop_all_games()
            await self.client.disconnect()
            logger.info("Userbot stopped")

async def start_userbot():
    """Start the userbot"""
    global _userbot_instance

    try:
        # Get environment variables
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        session_string = os.getenv('SESSION_STRING')

        if not all([api_id, api_hash, session_string]):
            logger.error("Missing required environment variables")
            return None

        # Create and start userbot
        userbot = WordleUserBot(int(api_id), api_hash, session_string)
        await userbot.start()

        _userbot_instance = userbot
        return userbot

    except Exception as e:
        logger.error(f"Failed to start userbot: {e}")
        return None

async def stop_userbot():
    """Stop the userbot"""
    global _userbot_instance

    if _userbot_instance:
        await _userbot_instance.stop()
        _userbot_instance = None

def get_userbot():
    """Get the current userbot instance"""
    return _userbot_instance
