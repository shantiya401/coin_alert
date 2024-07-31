# Crypto Alert Bot

## Overview

Crypto Alert Bot is a Telegram bot that allows users to set alerts for cryptocurrency price changes. Users can configure alerts for different conditions such as profit-taking, reminders, and stop-losses. The bot fetches real-time cryptocurrency prices using the Binance API and sends notifications to users when their alert conditions are met.

## Features

- **Set Alerts**: Users can set alerts for specific cryptocurrencies based on price targets.
- **Real-time Prices**: Fetches and displays the latest cryptocurrency prices from Binance.
- **Alert Types**: Supports different types of alerts including profit-taking, reminders, and stop-losses.
- **Manage Alerts**: Users can view, activate, delete, and edit their existing alerts.

## Getting Started

### Prerequisites

- Python 3.x
- `telebot` library for interacting with the Telegram Bot API
- `requests` library for fetching data from Binance API

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/crypto-alert-bot.git
Navigate to the project directory:

cd crypto-alert-bot
Install the required Python packages:

pip install -r requirements.txt
Configure your bot token and other settings in config.py.


Start the bot:

python bot.py
Interact with the bot on Telegram using the following commands:

/start: Start the bot and see the main menu.
/set_alert: Set a new alert.
/view_alerts: View your current alerts.
License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
Binance API for real-time cryptocurrency data.
Telegram Bot API for bot interactions.
