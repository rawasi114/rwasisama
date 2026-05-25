import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import helmet from 'helmet';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useLogger(app.get(Logger));

  const config = app.get(ConfigService);

  app.use(helmet());
  app.enableCors({
    origin: config.get<string>('CORS_ORIGIN', 'http://localhost:3000'),
    credentials: true,
  });
  app.setGlobalPrefix('api');
  app.useGlobalPipes(
    new ValidationPipe({ whitelist: true, transform: true, forbidNonWhitelisted: true }),
  );

  const swaggerConfig = new DocumentBuilder()
    .setTitle('Rawasi Sama ERP API')
    .setDescription('واجهة برمجة تطبيقات موديول الإنشاءات والمقاولات')
    .setVersion('0.1.0')
    .addBearerAuth()
    .build();
  const document = SwaggerModule.createDocument(app, swaggerConfig);
  SwaggerModule.setup('api/docs', app, document);

  // منصات الاستضافة (Render…) تحقن المنفذ عبر PORT؛ محلياً نستخدم API_PORT.
  const port = Number(process.env.PORT ?? config.get('API_PORT', 4000));
  await app.listen(port, '0.0.0.0');
  app.get(Logger).log(`🚀 API listening on http://localhost:${port}/api (docs: /api/docs)`);
}

void bootstrap();
