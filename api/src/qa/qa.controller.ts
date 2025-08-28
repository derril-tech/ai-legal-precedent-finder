import {
  Controller,
  Post,
  Body,
  Param,
  Get,
  UseGuards,
  Request,
  Res,
} from '@nestjs/common';
import { Response } from 'express';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { QaService } from './qa.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { AskQuestionDto } from './dto/ask-question.dto';

@ApiTags('qa')
@Controller('qa')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class QaController {
  constructor(private readonly qaService: QaService) {}

  @Post()
  @ApiOperation({ summary: 'Ask a legal question' })
  @ApiResponse({ status: 200, description: 'Question answered successfully' })
  async askQuestion(
    @Body() askQuestionDto: AskQuestionDto,
    @Request() req: any,
    @Res() res: Response,
  ) {
    // Set headers for Server-Sent Events
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Cache-Control');

    const sessionId = await this.qaService.createQaSession(
      askQuestionDto.question,
      req.user.id,
      req.user.workspaceId,
    );

    // Stream the answer
    await this.qaService.streamAnswer(sessionId, res);
  }

  @Get('answers/:id')
  @ApiOperation({ summary: 'Get answer by ID' })
  @ApiResponse({ status: 200, description: 'Answer retrieved successfully' })
  async getAnswer(@Param('id') id: string, @Request() req: any) {
    return this.qaService.getAnswer(id, req.user.workspaceId);
  }

  @Get('answers/:id/citations')
  @ApiOperation({ summary: 'Get answer citations' })
  @ApiResponse({ status: 200, description: 'Citations retrieved successfully' })
  async getAnswerCitations(@Param('id') id: string, @Request() req: any) {
    return this.qaService.getAnswerCitations(id, req.user.workspaceId);
  }
}
