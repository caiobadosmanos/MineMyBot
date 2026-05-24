const net = require('net');
const mineflayer = require('mineflayer');
const { Movements, pathfinder, goals: { GoalBlock, GoalXZ } } = require('mineflayer-pathfinder');
const minecraftData = require('minecraft-data');
const config = require('./settings.json');
const { logger } = require('./logging.js');

const [,, cliNick, cliHost, cliPort, cliVersion] = process.argv;
const username = cliNick || `Bot_${Math.floor(Math.random() * 10000)}`;
const serverHost = cliHost || config.server?.ip || 'localhost';
const serverPort = Number(cliPort || config.server?.port) || 25565;
const serverVersion = cliVersion || config.server?.version || '1.20.2';

function normalizeVersion(version) {
  if (!version) return '1.20.2';
  return String(version).replace(/_.+$/, '').split('-')[0];
}

function isServerReachable(host, port, timeout = 5000) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port, timeout }, () => {
      socket.destroy();
      resolve(true);
    });
    socket.on('error', () => {
      socket.destroy();
      resolve(false);
    });
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
  });
}

function resolveMcData(version) {
  const candidates = [version, normalizeVersion(version)];
  for (const candidate of candidates) {
    try {
      const mcData = minecraftData(candidate);
      if (mcData && mcData.blocksByName) {
        return mcData;
      }
    } catch (error) {
      continue;
    }
  }
  return null;
}

async function createBot() {
  const reachable = await isServerReachable(serverHost, serverPort);
  if (!reachable) {
    logger.error(`Servidor ${serverHost}:${serverPort} não está ativo ou não está aceitando conexões.`);
    return;
  }
  logger.info(`Creating bot with username=${username}, host=${serverHost}, port=${serverPort}, version=${serverVersion}`);

  const bot = mineflayer.createBot({
    username,
    host: serverHost,
    port: serverPort,
    version: serverVersion,
  });

  const versionToResolve = bot.version || serverVersion;
  const mcData = resolveMcData(versionToResolve);
  if (!mcData) {
    const versionStr = versionToResolve;
    logger.error(`minecraft-data não suporta a versão: ${versionStr}`);
    bot.emit('error', new Error(`Versão do Minecraft inválida ou não suportada: ${versionStr}`));
    return;
  }

  const shouldUsePathfinder = !!(
    config.position?.enabled ||
    config.utils?.['anti-afk']?.['circle-walk']?.enabled
  );
  let pathfinderEnabled = false;
  const defaultMove = shouldUsePathfinder ? new Movements(bot, mcData) : null;

  if (shouldUsePathfinder) {
    const wrappedPathfinder = (botArg, opts) => {
      try {
        pathfinder(botArg, opts);
        pathfinderEnabled = true;
      } catch (err) {
        logger.error(`Pathfinder plugin failed to load: ${err.message}`);
      }
    };
    bot.loadPlugin(wrappedPathfinder);
  }

  bot.once('inject_allowed', () => {
    if (bot.settings) {
      bot.settings.colorsEnabled = false;
    }
    if (pathfinderEnabled && bot.pathfinder && defaultMove) {
      bot.pathfinder.setMovements(defaultMove);
    }
  });

  bot.once('spawn', () => {
    logger.info('Bot joined to the server');

    if (config.utils?.['auto-auth']?.enabled) {
      const password = config.utils['auto-auth'].password || '';
      if (password) {
        logger.info('Started auto-auth module');
        setTimeout(() => {
          bot.chat(`/register ${password} ${password}`);
          bot.chat(`/login ${password}`);
        }, 500);
      } else {
        logger.warn('auto-auth habilitado, mas senha não foi definida.');
      }
    }

    if (config.utils?.['chat-messages']?.enabled) {
      const messages = config.utils['chat-messages']['messages'] || [];
      logger.info('Started chat-messages module');
      if (config.utils['chat-messages'].repeat) {
        const delay = Number(config.utils['chat-messages']['repeat-delay']) || 10;
        let i = 0;
        setInterval(() => {
          if (messages.length > 0) {
            bot.chat(messages[i]);
            i = (i + 1) % messages.length;
          }
        }, delay * 1000);
      } else {
        messages.forEach((msg) => bot.chat(msg));
      }
    }

    if (config.position?.enabled) {
      const pos = config.position;
      logger.info(`Starting moving to target location (${pos.x}, ${pos.y}, ${pos.z})`);
      if (bot.pathfinder) {
        bot.pathfinder.setGoal(new GoalBlock(pos.x, pos.y, pos.z));
      } else {
        logger.warn('Pathfinder não disponível; não é possível mover para a posição alvo.');
      }
    }

    if (config.utils?.['anti-afk']?.enabled) {
      const antiAfk = config.utils['anti-afk'];
      if (antiAfk.sneak) bot.setControlState('sneak', true);
      if (antiAfk.jump) bot.setControlState('jump', true);

      if (antiAfk?.hit?.enabled) {
        const delay = Number(antiAfk.hit.delay) || 5000;
        const attackMobs = antiAfk.hit['attack-mobs'];
        setInterval(() => {
          if (attackMobs) {
            const entity = bot.nearestEntity((e) => e.type !== 'object' && e.type !== 'player' && e.type !== 'global' && e.type !== 'orb' && e.type !== 'other');
            if (entity && typeof bot.attack === 'function') {
              bot.attack(entity);
              return;
            }
          }
          bot.swingArm('right', true);
        }, delay);
      }

      if (antiAfk.rotate) {
        setInterval(() => {
          bot.look(bot.entity.yaw + 1, bot.entity.pitch, true);
        }, 100);
      }

      if (antiAfk?.['circle-walk']?.enabled) {
        const radius = Number(antiAfk['circle-walk'].radius) || 5;
        if (bot.pathfinder) {
          circleWalk(bot, radius);
        } else {
          logger.warn('Pathfinder não disponível; circle-walk foi ignorado.');
        }
      }
    }
  });

  bot.on('chat', (username, message) => {
    if (config.utils?.['chat-log']) {
      logger.info(`<${username}> ${message}`);
    }
  });

  bot.on('goal_reached', () => {
    if (config.position?.enabled) {
      logger.info(`Bot arrived to target location. ${bot.entity.position}`);
    }
  });

  bot.on('death', () => {
    logger.warn(`Bot died and respawned at ${bot.entity.position}`);
  });

  if (config.utils?.['auto-reconnect']) {
    bot.on('end', () => {
      setTimeout(createBot, Number(config.utils['auto-reconnect-delay']) || 5000);
    });
  }

  bot.on('kicked', (reason) => {
    let reasonText = '';
    try {
      const parsed = JSON.parse(reason);
      reasonText = parsed.text || parsed.extra?.[0]?.text || String(reason);
    } catch {
      reasonText = String(reason);
    }
    reasonText = reasonText.replace(/§./g, '');
    logger.warn(`Bot was kicked from the server. Reason: ${reasonText}`);
  });

  bot.on('error', (err) => logger.error(err instanceof Error ? err.message : String(err)));
}

function circleWalk(bot, radius) {
  if (!bot.pathfinder) {
    logger.warn('Pathfinder não disponível; circleWalk não pode ser executado.');
    return;
  }
  const pos = bot.entity.position;
  const points = [
    [pos.x + radius, pos.y, pos.z],
    [pos.x, pos.y, pos.z + radius],
    [pos.x - radius, pos.y, pos.z],
    [pos.x, pos.y, pos.z - radius],
  ];
  let i = 0;
  setInterval(() => {
    if (i >= points.length) i = 0;
    bot.pathfinder.setGoal(new GoalXZ(points[i][0], points[i][2]));
    i += 1;
  }, 1000);
}

createBot().catch((err) => logger.error(`Falha ao iniciar o bot: ${err.message}`));
