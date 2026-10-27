<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $email = $_POST["email"];
    
    // Кому отправлять
    $to = "info@knopa.by";
    
    // Тема письма
    $subject = "Новая заявка с сайта knopa.by";
    
    // Текст письма
    $message = "Новый подписчик!\n\n";
    $message .= "Email: " . $email . "\n";
    $message .= "Дата: " . date("d.m.Y H:i:s") . "\n";
    $message .= "IP: " . $_SERVER['REMOTE_ADDR'] . "\n";
    
    // Заголовки
    $headers = "From: info@knopa.by\r\n";
    $headers .= "Reply-To: " . $email . "\r\n";
    $headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $headers .= "X-Mailer: PHP/" . phpversion();
    
    // Отправка
    if (mail($to, $subject, $message, $headers)) {
        echo "<!DOCTYPE html>
        <html>
        <head><meta charset='UTF-8'><title>Спасибо!</title>
        <style>
            body { font-family: 'Nunito', sans-serif; text-align: center; padding: 50px; background: #f8f4f9; }
            .box { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
            h1 { color: #f27a9c; font-size: 32px; }
            p { color: #5a4f61; font-size: 18px; }
            .btn { display: inline-block; margin-top: 20px; padding: 12px 30px; background: #f27a9c; color: white; border-radius: 50px; text-decoration: none; font-weight: 600; }
            .btn:hover { background: #e05f82; }
        </style>
        </head>
        <body>
        <div class='box'>
            <h1>🎉 Спасибо!</h1>
            <p>Мы получили ваш email. Как только платформа запустится — мы пришлём приглашение первыми.</p>
            <a href='/' class='btn'>Вернуться на сайт</a>
        </div>
        </body>
        </html>";
    } else {
        echo "Ошибка при отправке. Попробуйте ещё раз или напишите нам на info@knopa.by";
    }
}
?>