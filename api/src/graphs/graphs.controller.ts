import {
  Controller,
  Post,
  Body,
  Param,
  Get,
  UseGuards,
  Request,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { GraphsService } from './graphs.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { BuildGraphDto } from './dto/build-graph.dto';

@ApiTags('graphs')
@Controller('graphs')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class GraphsController {
  constructor(private readonly graphsService: GraphsService) {}

  @Post('build')
  @ApiOperation({ summary: 'Build precedent graph for a case' })
  @ApiResponse({ status: 201, description: 'Graph built successfully' })
  async buildGraph(
    @Body() buildGraphDto: BuildGraphDto,
    @Request() req: any,
  ) {
    return this.graphsService.buildGraph(
      buildGraphDto.case_id,
      req.user.workspaceId,
    );
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get precedent graph by ID' })
  @ApiResponse({ status: 200, description: 'Graph retrieved successfully' })
  async getGraph(@Param('id') id: string, @Request() req: any) {
    return this.graphsService.getGraph(id, req.user.workspaceId);
  }

  @Get(':id/visualization')
  @ApiOperation({ summary: 'Get graph visualization data' })
  @ApiResponse({ status: 200, description: 'Visualization data retrieved' })
  async getGraphVisualization(@Param('id') id: string, @Request() req: any) {
    return this.graphsService.getGraphVisualization(id, req.user.workspaceId);
  }
}
