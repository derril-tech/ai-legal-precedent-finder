import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from './auth/auth.module';
import { CasesModule } from './cases/cases.module';
import { QaModule } from './qa/qa.module';
import { GraphsModule } from './graphs/graphs.module';
import { SummariesModule } from './summaries/summaries.module';
import { ExportsModule } from './exports/exports.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL,
      entities: [__dirname + '/**/*.entity{.ts,.js}'],
      synchronize: process.env.NODE_ENV === 'development',
      logging: process.env.NODE_ENV === 'development',
    }),
    AuthModule,
    CasesModule,
    QaModule,
    GraphsModule,
    SummariesModule,
    ExportsModule,
  ],
})
export class AppModule {}
