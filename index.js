const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const cron = require('node-cron');

const client = new Client({ authStrategy: new LocalAuth() });

const userState = new Map();
let isGroupClosed = false;
let groupId = null;

const lecturesDir = 'C:\\Users\\IRIZI\\Desktop\\wha';
const metadataPath = path.join(lecturesDir, 'metadata.json');
const signature = "\n\n👨‍💻 *dev by: IRIZI 😊*";

// إذا ما كان موجود، أنشئ ملف metadata
if (!fs.existsSync(metadataPath)) fs.writeFileSync(metadataPath, JSON.stringify({}));

// تحميل البيانات الوصفية
function loadMetadata() {
    return JSON.parse(fs.readFileSync(metadataPath));
}

// حفظ البيانات الوصفية
function saveMetadata(data) {
    fs.writeFileSync(metadataPath, JSON.stringify(data, null, 2));
}

client.on('qr', qr => {
    console.log('📸 امسح رمز QR لتسجيل الدخول:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ العميل جاهز ومتصل!');
});

client.on('group_join', (notification) => {
    groupId = notification.chatId;
    console.log(`[📢] انضم للبوت إلى المجموعة: ${groupId}`);
});

async function isAdmin(userId, groupId) {
    const chat = await client.getChatById(groupId);
    if (!chat.isGroup) return false;

    if (!chat.participants) {
        await chat.fetchParticipants();
    }

    const admins = chat.participants?.filter(p => p.isAdmin || p.isSuperAdmin) || [];
    return admins.some(admin => admin.id._serialized === userId);
}

function getLecturesList() {
    return fs.readdirSync(lecturesDir).filter(file => file.endsWith('.pdf'));
}

cron.schedule('0 22 * * *', async () => {
    if (!isGroupClosed && groupId) {
        isGroupClosed = true;
        userState.clear();
        await client.sendMessage(groupId, '🚫 تم إغلاق المجموعة تلقائيًا الساعة 10:00 مساءً.' + signature);
    }
});

cron.schedule('0 8 * * *', async () => {
    if (isGroupClosed && groupId) {
        isGroupClosed = false;
        await client.sendMessage(groupId, '✅ تم فتح المجموعة تلقائيًا الساعة 8:00 صباحًا.' + signature);
    }
});

client.on('message_create', async message => {
    const userId = message.from;
    const contact = await message.getContact();
    const senderName = contact.pushname || contact.name || "مستخدم";
    const content = message.body.trim();
    const isGroupMessage = message.from.includes('@g.us');
    const currentGroupId = isGroupMessage ? message.from : groupId;

    const metadata = loadMetadata();

    if (message.hasMedia && message.type === 'document' && content) {
        // تخزين المحاضرة
        const media = await message.downloadMedia();
        const filename = `${Date.now()}_${message.filename}`;
        const filePath = path.join(lecturesDir, filename);

        fs.writeFileSync(filePath, Buffer.from(media.data, 'base64'));

        // إضافة وصف المحاضرة
        metadata[filename] = {
            name: message.filename,
            description: content
        };
        saveMetadata(metadata);

        await message.reply(`✅ تم حفظ المحاضرة *${message.filename}* بنجاح مع الوصف!` + signature);
        return;
    }

    if (isGroupClosed && content.toLowerCase() !== 'فتح المجموعة' && isGroupMessage) {
        await message.reply(`🚫 المجموعة مغلقة حالياً، يا ${senderName}. الرجاء الانتظار.` + signature);
        return;
    }

    if (content.toLowerCase() === 'إغلاق المجموعة' && isGroupMessage) {
        const isUserAdmin = await isAdmin(userId, currentGroupId);
        if (!isUserAdmin) {
            await message.reply(`❌ عذرًا ${senderName}، هذا الأمر للمشرفين فقط!` + signature);
            return;
        }

        if (isGroupClosed) {
            await message.reply(`⚠️ المجموعة مغلقة بالفعل، يا ${senderName}.` + signature);
        } else {
            isGroupClosed = true;
            userState.clear();
            await message.reply(`🚫 تم إغلاق المجموعة بواسطة ${senderName}!` + signature);
        }
        return;
    }

    if (content.toLowerCase() === 'فتح المجموعة' && isGroupMessage) {
        const isUserAdmin = await isAdmin(userId, currentGroupId);
        if (!isUserAdmin) {
            await message.reply(`❌ عذرًا ${senderName}، هذا الأمر للمشرفين فقط!` + signature);
            return;
        }

        if (!isGroupClosed) {
            await message.reply(`⚠️ المجموعة مفتوحة بالفعل، يا ${senderName}.` + signature);
        } else {
            isGroupClosed = false;
            await message.reply(`✅ تم فتح المجموعة بواسطة ${senderName}!` + signature);
        }
        return;
    }

    if (content.toLowerCase() === 'pdf' && isGroupMessage) {
        const lectures = getLecturesList();
        if (lectures.length === 0) {
            await message.reply(`📂 لا توجد محاضرات حالياً، يا ${senderName}.` + signature);
            return;
        }

        let lectureList = '📚 قائمة المحاضرات:\n';
        lectures.forEach((lecture, index) => {
            const title = metadata[lecture]?.name || lecture;
            lectureList += `${index + 1}. ${title}\n`;
        });
        lectureList += `\n✉️ أرسل رقم المحاضرة اللي تبيها يا ${senderName} (مثال: 1)`;

        userState.set(userId, { step: 'select_lecture', lectures });
        await message.reply(lectureList + signature);
        return;
    }

    if (userState.has(userId) && isGroupMessage) {
        const state = userState.get(userId);

        if (state.step === 'select_lecture') {
            const lectureIndex = parseInt(content) - 1;
            if (lectureIndex >= 0 && lectureIndex < state.lectures.length) {
                const selectedLecture = state.lectures[lectureIndex];
                const pdfPath = path.join(lecturesDir, selectedLecture);

                if (fs.existsSync(pdfPath)) {
                    const media = MessageMedia.fromFilePath(pdfPath);
                    const description = metadata[selectedLecture]?.description || 'بدون وصف';

                    await client.sendMessage(userId, media, {
                        caption: `📎 المحاضرة: ${metadata[selectedLecture]?.name || selectedLecture}\n📝 الوصف: ${description}${signature}`
                    });
                } else {
                    await message.reply(`❌ الملف غير موجود، يا ${senderName}.` + signature);
                }

                userState.delete(userId);
            } else {
                await message.reply(`⚠️ رقم غير صحيح يا ${senderName}! حاول مرة ثانية.` + signature);
            }
        }
    }
});

client.initialize()
    .then(() => console.log('🚀 تم تشغيل البوت بنجاح!'))
    .catch(err => console.error('❌ خطأ أثناء التشغيل:', err));
