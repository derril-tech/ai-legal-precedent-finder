import {
  Controller,
  Get,
  Param,
  UseGuards,
  Request,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { SummariesService } from './summaries.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('summaries')
@Controller('summaries')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class SummariesController {
  constructor(private readonly summariesService: SummariesService) {}

  @Get(':case_id')
  @ApiOperation({ summary: 'Get case summaries' })
  @ApiResponse({ status: 200, description: 'Summaries retrieved successfully' })
  async getCaseSummaries(@Param('case_id') caseId: string, @Request() req: any) {
    return this.summariesService.getCaseSummaries(caseId, req.user.workspaceId);
  }

  @Get(':case_id/holdings')
  @ApiOperation({ summary: 'Get case holdings summary' })
  @ApiResponse({ status: 200, description: 'Holdings summary retrieved' })
  async getHoldingsSummary(@Param('case_id') caseId: string, @Request() req: any) {
    return this.summariesService.getHoldingsSummary(caseId, req.user.workspaceId);
  }

  @Get(':case_id/reasoning')
  @ApiOperation({ summary: 'Get case reasoning summary' })
  @ApiResponse({ status: 200, description: 'Reasoning summary retrieved' })
  async getReasoningSummary(@Param('case_id') caseId: string, @Request() req: any) {
    return this.summariesService.getReasoningSummary(caseId, req.user.workspaceId);
  }

  @Get(':case_id/dicta')
  @ApiOperation({ summary: 'Get case dicta summary' })
  @ApiResponse({ status: 200, description: 'Dicta summary retrieved' })
  async getDictaSummary(@Param('case_id') caseId: string, @Request() req: any) {
    return this.summariesService.getDictaSummary(caseId, req.user.workspaceId);
  }
}
